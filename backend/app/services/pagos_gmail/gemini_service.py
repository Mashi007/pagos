"""
Gemini: enviar imagen o PDF, extraer datos de comprobantes.
Usa el paquete google-genai (google.genai) — sucesor de google-generativeai.
Configuración única para todo el sistema: GEMINI_API_KEY y GEMINI_MODEL (app.core.config.settings).

- Pagos (Gmail): fecha_pago, cedula, monto, numero_referencia (extract_payment_data).
- Cobranza (papeleta/informe): fecha_deposito, nombre_banco, etc. (extract_cobranza_from_image).
- Cobros (reporte público): comparar datos del formulario vs imagen del comprobante (compare_form_with_image).
  Cobros usa la misma API key y modelo que el resto del sistema; sin clave, los reportes van a en_revision.
"""
import io
import json
import logging
import re
import time
from typing import Any, Dict, Literal, Optional, Tuple

GEMINI_RATE_LIMIT_RETRY_DELAY = 45
GEMINI_RATE_LIMIT_MAX_RETRIES = 2
GEMINI_SERVER_ERROR_RETRY_DELAY = 15  # Para 503 Server Unavailable
GEMINI_SERVER_ERROR_MAX_RETRIES = 4  # Máximo 4 reintentos para 503

from app.core.config import settings
from app.services.pagos_gmail.helpers import extract_sender_email, get_mime_type

logger = logging.getLogger(__name__)

PAGOS_NA = "NA"

PagosGmailFormato = Literal["A", "B", "C", "ninguno"]

GEMINI_PAGOS_GMAIL_FORMATO_Y_EXTRACCION = """
Eres un clasificador estricto. Entrada: una sola imagen o PDF extraida del mensaje (incrustada en cuerpo, adjunto con nombre,
o comprobante dentro de un correo reenviado .eml). No uses asunto del correo ni texto del cuerpo para clasificar ni rellenar,
salvo un bloque literal "CONTEXTO_REMITE:" que SOLO puedes usar en formato C para el campo email_cliente cuando en la captura Binance no se lea el email del destinatario.
Si hay duda -> formato "ninguno" y los cuatro campos "NA". No inventes datos.

ORIGEN EN GMAIL (embebida vs adjunta): misma regla en todos los casos.
  Cada peticion te envia UN solo binario (una imagen o un PDF). Ese binario puede proceder de:
    (a) adjunto clasico al mensaje,
    (b) imagen incrustada en el HTML del cuerpo (inline / CID / multipart related),
    (c) imagen detectada dentro del cuerpo sin filename util,
    (d) PDF adjunto o pagina de PDF, o trozo extraido de un .eml reenviado.
  No importa el origen: si el contenido visual es plantilla A, B o C (Binance Pay), clasifica igual. No descartes por "parece pegado en el correo" o "no es adjunto".
  Nombres genericos del sistema (inline-0.jpg, image.png, unnamed, parte sin titulo) NO son evidencia de ninguno; solo cuenta lo que se ve en los pixeles.
  Si ves chrome de cliente de correo (cabeceras, botones, fondo gris) alrededor pero el ticket o recibo BNC/RAPI es legible en el centro, ignora el marco y lee el comprobante.
  Si el binario es solo firma, logo, banner, avatar o recorte sin los datos de operacion, o el comprobante esta tan cortado que no puedes los cuatro campos con certeza -> ninguno.
  Las imagenes embebidas suelen tener mas compresion o menos dpi: tolera OCR sucio (guiones rotos, letras pegadas) pero si un campo sigue ilegible -> ninguno, no rellenes por contexto del correo.

CORREO CON MAS DE UNA IMAGEN O MAS DE UN PDF:
  El backend procesa cada binario por separado (una peticion = un solo archivo). Aunque el correo tenga 2, 3 o mas capturas adjuntas o embebidas, tu SOLO ves el de esta peticion.
  REGLA: 1 imagen (o 1 PDF de una pagina relevante) = como maximo 1 clasificacion y 1 JSON = 1 pago en Excel. No agrupes varias capturas en un solo resultado; no rellenes campos con datos que "imaginas" de otras imagenes del mismo mensaje.
  Cada binario se evalua con las MISMAS reglas de plantilla: A (imagen 1), B (imagen 2), C (imagen 3 / Binance) o ninguno. Una pieza puede ser A, otra del mismo correo B y otra ninguno: es correcto e independiente.
  Si esta pieza es basura (firma, icono, segunda copia ilegible) -> ninguno; no intentes completar un pago usando otra captura que no esta en pantalla.

OBLIGATORIO — campo "formato" en el JSON: SOLO uno de estos cuatro valores exactos: A, B, C, ninguno.
  A = plantilla imagen 1: ticket RAPI-CREDIT / RECAUDACION / terminal (abajo) O papeleleta Mercantil DEPOSITO DIVISAS a RAPI-CREDIT con RECAUDACION (VARIANTE MERCANTIL).
  B = unicamente plantilla imagen 2 (recibo BNC a favor de RAPI-CREDIT descrita abajo).
  C = plantilla imagen 3: pantalla Binance Pay "Pago completado" con visto verde (circulo + check) descrita en PASO 2b y FORMATO C.
  ninguno = cualquier otra cosa, duda, borroso, selfie, documento que no sea esas tres plantillas.
Prohibido usar otro valor en "formato" (ni numeros, ni texto libre).

REGLA SISTEMA A/B: Devuelve "A" o "B" solo si el comprobante coincide con imagen 1 o 2 y puedes extraer los CUATRO campos con valor real
(fecha_pago, cedula, monto, numero_referencia). Si la plantilla parece A o B pero algun campo no es legible, formato "ninguno" y NA.

REGLA SISTEMA C (imagen 3 / Binance Pay): Devuelve "C" solo si ves el nucleo C (PASO 2b) y puedes extraer con certeza:
  monto (USDT/USD), numero_referencia (Id. de la orden / Order ID), y email_cliente (visible en pantalla; si no se lee, solo formato C puede usar el bloque literal CONTEXTO_REMITE descrito arriba).
  Para formato C en el JSON pon siempre fecha_pago="NA" y cedula="NA" (no inventes; el sistema asigna fecha desde el correo y cedula desde tabla clientes por email).
  Si falta monto, id de orden o email legible -> formato "ninguno" y todos los campos relevantes NA.

COLUMNAS OBLIGATORIAS Y GMAIL (estrella / etiquetas — las aplica el backend):
  A y B: las cuatro columnas fecha_pago, cedula, monto, numero_referencia deben ser reales en tu respuesta; si falta una -> ninguno.
  C: monto, numero_referencia, email_cliente obligatorios; fecha_pago y cedula deben ser "NA" en JSON.
  El pipeline evalua cada imagen/PDF por separado: varias piezas validas en un correo generan varias filas (una por pieza que cumpla A, B o C). Solo estrella y etiqueta cuando TODAS las piezas del correo alcanzan estado final (ver logica del backend); en C, si el email no existe en clientes, el backend no incorpora fila ni etiqueta para esa pieza (no es tu tarea verificar la base de datos).

=== CLASIFICACION EN ORDEN (sigue el orden; no inviertas B y A) ===
Objetivo: decidir formato en pocas comprobaciones. Cada peticion es UNA sola pieza: clasifica solo lo visible ahi; mismas reglas imagen 1 (A), imagen 2 (B) e imagen 3 (C) que si el correo tuviera un unico archivo. No cruces datos entre capturas.

PASO 1 - DESCARTE (ninguno al instante):
  No aparece RAPI-CREDIT (ni RAPI CREDIT / RAPICREDIT / RAPH-CREDIT / RAPICREDI razonable) y tampoco BNC reconocible
    y tampoco es la variante Mercantil DEPOSITO DIVISAS descrita en "VARIANTE A — MERCANTIL" abajo
    y tampoco es pantalla Binance Pay imagen 3 (PASO 2b) -> ninguno.
  Es captura de app generica, Pago Movil no Binance Pay, Zelle, otro banco distinto (salvo Mercantil con RAPI+RECAUDACION), selfie, publicidad, borroso sin datos -> ninguno.
  Excepcion: NO descartes como "solo app" si cumple nucleo C (Binance + Pago completado + visto verde + USDT + orden + email).

PASO 2 - Prioridad B (imagen 2) si el nucleo B se cumple; entonces B, no A ni C:
  Nucleo B = (BNC logo o texto) + cuenta con barras ####/####/##/######## (ej. 0191/0127/...) + RAPI-CREDIT como titular o beneficiario de esa cuenta
    + monto en dolares visible (Us$, US$, USD, o patron *...*NN.mm con decimales).
  Si el nucleo B se cumple, elige B aunque tambien aparezca "RAPI-CREDIT" en otro contexto: aqui es recibo de cajero BNC, no ticket RECAUDACION.
  Refuerzos utiles de B (opcionales si el nucleo ya es claro): asteriscos antes del monto; Agencia / Terminal / Cajero; "Serial:"; ristra solo digitos >12 que empiece en 7.
  REGLA FIJA — linea DP + recibo BNC: Si el papel es claramente **recibo de cajero BNC** (sello o texto legible "Banco Nacional de Credito" / "Banco Nacional de Crédito" / marca BNC,
    fondo con lineas azules o patron de matriz de cajero, cuenta ####/####/##/######## con RAPI como titular, tipico comprobante horizontal BNC)
    **y** en la misma pieza aparece la linea del depositante **DP:** seguida de **V-** o **E-** o **J-** y digitos de cedula **con el nombre en la misma linea**
    (ej. `DP: V-015185092` y a continuacion `MIRAIDA JIMENEZ`, con o sin guion entre cedula y nombre) -> **formato B (imagen 2) SIEMPRE**, **nunca A (imagen 1)**,
    aunque el OCR tambien capte "RAPI" o "RAPI CREDIT" (en BNC es titular de cuenta, no ticket RECAUDACION vertical). Esta regla prevalece sobre "DP:...-NOMBRE refuerza A".
  REGLA FIJA — **Banco Mercantil = imagen 1 (A)**, no B: Si la cuenta cliente o el comprobante muestra codigo **0105** al inicio del numero de cuenta
    (formato `0105-0120-22-5120135978`, `0105 0120 22 5120135978`, `0105 0121 21 ...` u OCR sucio parecido), eso es **Banco Mercantil** en Venezuela -> **formato A** (variante Mercantil o ticket RECAUDACION), **nunca B (BNC)**.
    Aplica a: (1) **tira termica/validador** vertical u orientada (SPD/DCME/HOME, Cedula Dep., Fondo RECAUDACION, RAPI-CREDIT o OCR "RAPH-CREDIT"); (2) **formulario papel "DEPOSITO DIVISAS" / "DEPÓSITO DIVISAS"** con logo **Mercantil** y tira impresa con Refer/Serial/Monto USD/RECAUDACION.
    El recibo BNC tipico usa cuenta destino con otro codigo de entidad en el patron cajero (ej. **0191**/... con slashes), no confundir con 0105 Mercantil.

PASO 2b - C (imagen 3 / Binance Pay) si PASO 2 no aplico (no es recibo BNC):
  Nucleo C = interfaz Binance (tema oscuro frecuente) + titulo "Pago completado" o "Payment completed"
    + distintivo superior: circulo VERDE con marca de verificado / visto (check) centrado (icono de exito de la app)
    + importe principal en USDT o USD (ej. "122 USDT", "50.5 USDT", "135 USDT")
    + ideal: seccion destinatario con correo visible (usuario@dominio) y linea "Id. de la orden" / "Order ID" / "ID de orden" con numero largo (solo digitos).
  Si la captura esta recortada o comprimida: con visto verde + "Pago completado" + importe USDT/USD claro, sigue siendo C.
    - numero_referencia: usa el Id. de orden completo si lo ves; si no, cualquier bloque de 15+ digitos que parezca identificador de orden/transaccion Binance en la misma pantalla.
    - email_cliente: si el email del destinatario NO se lee en la imagen pero recibes CONTEXTO_REMITE: con una direccion, copia esa direccion en email_cliente (minusculas).
  NO es C: login, historial sin pantalla de completado, otra exchange, sin visto verde + sin titulo de completado, captura ilegible.
  Si nucleo C: formato C (no A ni B). Extraccion: monto, numero_referencia, email_cliente (visible o desde CONTEXTO_REMITE); fecha_pago=NA; cedula=NA.

PASO 3 - A (imagen 1) solo si PASO 2 y 2b no aplicaron:
  Nucleo A (terminal / ticket clasico) = RAPI-CREDIT + RECAUDACION (con o sin tilde en OCR) + USD + ticket de recaudacion (vertical/monoespaciado tipico) + grupos FORMATO A (1-5).
  Serial operacion: bloques separados por guiones con 2do bloque = fecha 8 digitos YYYYMMDD.
  Patron fuerte A: misma linea DP:...-NOMBRE APELLIDO (cedula y nombre juntos).
  Nucleo A (Mercantil papel): ver VARIANTE A — MERCANTIL; si se cumple, es formato A aunque el banco sea Mercantil y no BNC.

PASO 4 - Desempate si queda duda entre A y B (si ya clasificaste C en 2b, no uses este paso):
  Cuenta 0191/... + BNC + RAPI titular + cajero/agencia -> B gana.
  Asteriscos + decimales + Debito/Us$ en contexto BNC -> B.
  RECAUDACION + serial con 2do bloque YYYYMMDD + sin recibo BNC de cuenta con slashes -> A.
  Cedula+nombre misma linea (DP:... + V-/E-/J- + nombre) + ticket **vertical** RECAUDACION + serial YYYYMMDD **sin** evidencia de recibo BNC cajero -> A.
  Si aplica la REGLA FIJA del PASO 2 (DP + contexto BNC) -> B; no uses esta linea para forzar A.

PASO 5 - Extraccion: A o B solo si los cuatro campos son legibles; C solo si monto + numero_referencia + email_cliente son legibles y pones fecha y cedula en NA; si no, ninguno y NA.

DISCRIMINADOR SERIAL — imagen 1 (A) vs imagen 2 (B) (aplica ademas de RAPI-CREDIT/BNC):
  IMAGEN 1 / A — serial de operacion compuesto por BLOQUES separados por guiones (-) u ocasionalmente /:
    El SEGUNDO bloque (contando de izquierda a derecha o de arriba a abajo en texto vertical) debe ser
    una FECHA como 8 digitos YYYYMMDD (ej. 20260401 = 1 abr 2026). Ejemplo de patron: 9813-20260401-144545-DCME-7643-A.
    Puede incluir DCME, SPDP, letras sueltas al final. Esto NO es una sola ristra de 13+ digitos.
  VARIANTE MERCANTIL (sigue siendo A / imagen 1): en papeleleta "DEPOSITO DIVISAS" / "DEPÓSITO DIVISAS" (Mercantil) a favor de RAPI-CREDIT con Fondos RECAUDACION,
    suele aparecer ADEMAS una linea impresa "Serial:" (o similar OCR: Serlal, Serial) con una cadena de SOLO digitos, a menudo 13+ cifras empezando por 7 (ej. 740087418878065).
    Esa ristra larga en contexto Mercantil+RAPI+RECAUDACION+USD NO es plantilla B: es el numero de operacion del deposito en divisas. Usala como numero_referencia (valor completo, solo digitos) cuando sea el identificador principal visible junto al serial del deposito.
    Si coexisten (1) cadena con guiones y 2do bloque YYYYMMDD tipo 9213-20260331-143046-DCME-0154-A y (2) Serial: 7400... largo, prefiere el Serial largo (digitos) como numero_referencia para esta variante Mercantil, salvo que solo uno sea legible.
  IMAGEN 2 / B — identificador largo numerico:
    En **recibo BNC** (no Mercantil): cadena de SOLO digitos con MAS DE 12 cifras que EMPIEZA POR 7 (ej. 74087406582990),
    a veces en margen vertical. Señal fuerte de plantilla B cuando va con logo BNC + cuenta ####/####/##/######## + RAPI titular.
  Si el comprobante cumple criterios de A (terminal) y la linea serial sigue el patron guiones+fecha en 2do bloque -> A.
  Si cumple BNC (no Mercantil DEPOSITO DIVISAS) y aparece la ristra larga que empieza en 7 (>12 digitos) -> priorizar B y usar esa ristra en numero_referencia si es el id principal.

DISCRIMINADOR CEDULA / MONTO — imagen 1 (A) vs imagen 2 (B):
  IMAGEN 1 / A (ticket recaudacion RAPI-CREDIT **vertical**): En la linea del depositante la CEDULA va JUNTO AL NOMBRE en la MISMA linea,
    casi siempre separados por un guion: ej. DP:V-015185092-MIRAIDA JIMENEZ o DP: V-... seguido de guion y nombre en mayusculas.
    Ese patron refuerza **A solo** en ticket de **terminal/recaudacion** (monoespaciado vertical, RECAUDACION, serial con YYYYMMDD en 2do bloque).
    Si el mismo patron DP: V-... + nombre aparece en **recibo BNC horizontal** con sello/agua Banco Nacional de Credito -> es **B (imagen 2)**, ver REGLA FIJA PASO 2.
  No confundir con solo etiqueta "Cedula Dep" sin nombre en la misma linea.
  VARIANTE MERCANTIL (A): La cedula puede estar en varias zonas: (1) impreso "Cedula Dep." / "Cédula Dep" con solo digitos (ej. 0028424570) — normaliza a V/E/J + digitos sin ceros a la izquierda tras letra;
    (2) manuscrito en casillas "Nro. de Cédula" con puntos miles (ej. 28.424.570) — quita puntos y prefijo V si aplica;
    (3) nombre del depositante puede ir manuscrito en "Depositante" e impreso en mayusculas abreviada en la tira del cajero — usa la cedula mas clara y consistente.
  En Mercantil DEPOSITO DIVISAS el monto en USD puede ir con asteriscos en la tira impresa (ej. ***********96,00 USD) usando COMA como decimal venezolano; extrae 96.00 USD. Puede coexistir monto manuscrito "96" en casilla — prioriza la linea impresa del sistema si es legible.
  IMAGEN 2 / B (recibo BNC): El MONTO en dolares del deposito casi SIEMPRE aparece con ASTERISCOS (*) inmediatamente antes
    del valor numerico con decimales, ej. **********122.00 o *****96.00 (cantidad de asteriscos variable). Es señal fuerte de plantilla B.
    En A el importe puede mostrarse con USD sin esa cortina de asteriscos tipica de cajero BNC; si ves BNC + linea Debito/Us$ + asteriscos+monto -> B.

FORMATO A — palabras clave y grupos (deben cumplirse TODOS los grupos 1-5):
  Grupo 1 (empresa): RAPI-CREDIT | RAPI CREDIT | RAPI-CREDIT, C.A. | RAPICREDIT | RAPICREDI | RAPH-CREDIT (OCR sucio: H por I, falta guion)
  Grupo 2 (concepto): RECAUDACION | RECAUDACIÓN (tolerar sin tilde: RECAUDACION)
  Grupo 3 (moneda): USD en linea de monto o junto al importe
  Grupo 4 (depositante): CEDULA DEP | Cédula Dep | DP:V-... y en la MISMA linea el NOMBRE del depositante tras guion (patron fuerte imagen 1)
  Grupo 5 (operacion): linea de monto con USD (sin exigir asteriscos como en B) y serial con bloques separados por guiones;
    numero_referencia conserva guiones y 2do bloque YYYYMMDD cuando sea visible.
Palabras secundarias A (refuerzo, no bastan solas): FONDOS, CANT BILLETES, COMISION, TASA, CTA. COM,
  DCME, SPDP, COPIA (vertical), lineas alfanumericas tipo XXXX-YYYYMMDD-hhmmss-...

VARIANTE A — MERCANTIL (dos caras tipicas; ambas son formato A / imagen 1, banco Mercantil):
  (A1) **Formulario papel DEPOSITO DIVISAS**: logo o nombre **Mercantil**; titulo "DEPOSITO DIVISAS" o "DEPÓSITO DIVISAS"; casillas manuscritas (depositante, cedula, monto); tira del validador pegada o impresa con Refer, Monto USD, Fondo RECAUDACION, RAPI-CREDIT/RAPICREDI, Cédula Dep.
  (A2) **Solo tira termica / comprobante de cajero Mercantil**: texto monoespaciado o vertical; lineas **Cedula Dep.**, **Cant. Billetes**, **Comision**, **Tasa**; cuenta tipo **0105-....-..-..........**; destino RAPI/RAPH-CREDIT + **RECAUDACION**; serial largo solo digitos (ej. 7403...) y/o cadena con guiones con bloque **YYYYMMDD**.
  Reconocimiento visual comun: cabecera o marca Banco Mercantil / MERCANTIL / "Mercantil, C.A." cuando aparece en (A1); en (A2) basta **0105** + RAPI + RECAUDACION en la tira.
  Beneficiario / empresa destino en la tira impresa: RAPI-CREDIT, C.A. o RAPI-CREDIT (misma familia que Grupo 1).
  Fondos / concepto impreso: RECAUDACION (u OCR sucio RECAUDACION).
  Moneda: checkbox o texto USD / dolares en el formulario; monto en USD en tira (asteriscos + NN,dd USD con coma decimal) o casilla manuscrita.
  Grupos equivalentes para esta variante: (1) RAPI-CREDIT como destino, (2) RECAUDACION en fondos, (3) USD, (4) cedula legible (impresa y/o manuscrita), (5) referencia: linea Serial larga digitos y/o codigo operacion con guiones YYYYMMDD en 2do bloque.
  Cuenta cliente en casillas o en tira (ej. 0105 0120 22 5120135978 o 0105-0120-22-5120135978) NO es numero_referencia; no confundir con serial de operacion. **0105** confirma institucion Mercantil para campo banco en JSON (ej. "Mercantil" o "Banco Mercantil").
  fecha_pago: usar fecha de la operacion en tira (2do bloque YYYYMMDD si aparece en el codigo guionado) o fecha manuscrita "31/3/2026" en el formulario si la tira es ilegible — una sola fecha coherente DD/MM/YYYY.
  Si cumple esta variante Mercantil, clasifica A (no "ninguno" por ser banco Mercantil; no B salvo que cumpla nucleo BNC completo de PASO 2).

FORMATO B — comprobante BNC de deposito a favor de RAPI-CREDIT (segunda plantilla valida; horizontal u horizontal-corta):
  Plantilla tipica (reconoce aunque el orden de lineas varie un poco):
    - Esquina superior izquierda o cabecera: logo/texto BNC.
    - Puede haber referencia arriba a la derecha (numero distinto al serial).
    - Lineas tipo: Agencia: ... | Terminal: ... | Cajero: ... (nombres de cajero frecuentes).
    - Fecha y hora de operacion en una linea (ej. DD/MM/YYYY HH:MM:SS).
    - Etiqueta Serial: seguida de digitos (serial de operacion).
    - Cuenta del beneficiario con barras: patron ####/####/##/########## (ej. 0191/0127/48/2300080639).
    - Titular de la cuenta visible como RAPI-CREDIT, C.A. | RAPI-CREDIT C.A. | RAPI-CREDIT (misma familia que formato A pero aqui es CUENTA DESTINO en recibo BNC, no ticket de recaudacion).
    - Depositante: linea DP:V-######## o DP:E-... (la cedula puede ir sola o con nombre; en B el recibo es horizontal BNC).
    - Monto (señal fuerte imagen 2): el importe en dolares CASI SIEMPRE va precedido de ASTERISCOS antes de los digitos y decimales,
      ej. **********122.00, *****96.00; suele acompañar texto tipo Debito Us$ | Us$ | US$. Lee el monto ignorando los asteriscos.
      Si ves esta cortina de asteriscos + decimales en contexto BNC, clasifica B y extrae solo la cifra (ej. 122.00 USD).
    - Fondo con patron gris repetido (floral/hojas) y texto impreso tipo matriz de puntos; sello azul
      "Banco Nacional de Credito" opcional — refuerza B pero no es obligatorio si el resto coincide.
  Criterio B (minimo): BNC + cuenta con slashes tipo 0191/... + RAPI-CREDIT como beneficiario/titular
    + indicio claro de dolares (Us$, US$, USD, o monto con **... y decimales tipo deposito) + Agencia o Terminal/Cajero o Serial.
  NO es B si es otro banco, solo captura de app, o BNC sin RAPI-CREDIT en la zona de cuenta/beneficiario.

  Diferencia A vs B: A = ticket RAPI-CREDIT RECAUDACION; B = recibo BNC donde RAPI-CREDIT es titular de cuenta destino.
    Ya decidiste con PASO 2-4 arriba; aqui el detalle de plantilla.

Resumen discriminadores (cruce con PASO 4): serial 2do bloque YYYYMMDD -> A; ristra >12 digitos empezando en 7 + BNC + cuenta slashes -> fuerte B;
  cuenta que empieza en **0105** + RAPI + RECAUDACION (tira o formulario) -> **A Mercantil**, no B;
  misma ristra larga 7400... pero Mercantil + DEPOSITO DIVISAS + RAPI + RECAUDACION -> A (variante Mercantil).
  Cedula+nombre misma linea DP:...-NOMBRE -> A; monto *...*122.00 con BNC -> fuerte B.

DESCARTE (refuerzo PASO 1): sin RAPI-CREDIT ni BNC ni nucleo Binance C -> ninguno.
  Ticket A completo pero sin recibo BNC -> A si grupos 1-5 OK; si falta grupo obligatorio de A -> ninguno.
  Recibo BNC + RAPI titular + dolares -> B aunque no diga literal "Deposito Us$".
  Pantalla Binance Pay nucleo C -> C aunque no haya RAPI-CREDIT en la captura.

=== DETALLE FORMATO A ===
Ticket vertical, fuente monoespaciada. Los 5 grupos de palabras clave arriba deben verse; el margen
"Copia"/SPDP ayuda pero no sustituye empresa+recaudacion+USD+cedula+monto/serial.
cedula: extraela de la linea DP:... donde vaya seguida de guion y nombre del depositante en la misma linea (imagen 1).
  En VARIANTE MERCANTIL: prioriza Cédula Dep impresa; si solo hay digitos, antepone V salvo que el comprobante indique E/J.
numero_referencia: la cadena completa del serial con guiones tal como en el comprobante; verifica que el segundo
  bloque separado por guiones sea 8 digitos fecha (YYYYMMDD). Si OCR pierde guiones, reconstruye la estructura
  minima para que el 2do segmento sea la fecha legible.
  En VARIANTE MERCANTIL: si existe "Serial:" con solo digitos (13+ cifras tipico), usa esa cadena completa como numero_referencia; si ademas hay 9213-YYYYMMDD-...-DCME-..., el Serial largo tiene prioridad.
monto: en Mercantil con coma decimal (96,00) devuelve equivalente con punto para el JSON si el esquema lo requiere (ej. 96.00 USD).

=== DETALLE FORMATO B ===
Prioriza la plantilla horizontal BNC anterior. numero_referencia: si hay ristra numerica de mas de 12 digitos
  que empiece por 7 (identificador largo), usala como numero_referencia; si no, usa el valor junto a "Serial:".
  Si hay referencia corta arriba a la derecha y Serial de cajero, prefiere la ristra larga que empiece en 7 cuando exista.
  monto: patron tipico imagen 2 = asteriscos seguidos de NN.mm; extrae NN.mm y devuelve ej. 122.00 USD (sin asteriscos en JSON).
  fecha_pago: fecha/hora impresa de la operacion.

=== DETALLE FORMATO C (imagen 3 / Binance Pay) ===
  Banco en Excel lo fija el sistema como BINANCE; no hace falta devolver campo banco en JSON.
  monto: lee cifra con USDT o USD (ej. 122 USDT -> "122.00 USDT" o "122 USDT" consistente).
  numero_referencia: copia entera el Id. de la orden (digitos; no omitas digitos por OCR).
  email_cliente: un solo email, minusculas opcional; debe coincidir con texto visible en pantalla (destinatario del pago).
  fecha_pago: "NA". cedula: "NA".

=== EXTRACCION ===
A/B: fecha_pago, cedula (normaliza V/E/J + digitos; en A prioriza linea DP:...-NOMBRE),
  monto con moneda (B: cifra tras asteriscos + USD; A: USD segun comprobante),
  numero_referencia segun plantilla A o B. email_cliente puede ser "NA".
  banco: nombre de la INSTITUCION del comprobante (como aparece: logo, cabecera, pie de pagina).
    Ejemplos: formato B con logo BNC -> "BNC" o "Banco Nacional de Credito"; variante Mercantil (DEPOSITO DIVISAS) -> "Mercantil" o "Banco Mercantil";
    ticket RECAUDACION RAPI si ves nombre de banco en el ticket usalo; si solo dice RAPI sin banco legible -> "NA".
C: monto, numero_referencia, email_cliente obligatorios; fecha_pago="NA"; cedula="NA".

Salida: solo JSON, sin markdown.
  A/B: {"formato":"A"|"B","fecha_pago":"...","cedula":"...","monto":"...","numero_referencia":"...","email_cliente":"NA","banco":"Mercantil"|"BNC"|"..."}
  C: {"formato":"C","fecha_pago":"NA","cedula":"NA","monto":"...","numero_referencia":"...","email_cliente":"usuario@dominio.com","banco":"NA"}
  ninguno: {"formato":"ninguno","fecha_pago":"NA","cedula":"NA","monto":"NA","numero_referencia":"NA","email_cliente":"NA","banco":"NA"}
""".strip()

# Estos formatos pasan a Drive/BD/etiquetas IMAGEN 1 / 2 / 3 (C requiere ademas cedula por email en clientes).
PAGOS_GMAIL_FORMATOS_PLANTILLA: frozenset[str] = frozenset({"A", "B", "C"})


GEMINI_PROMPT = (
    "[EN] You MUST review ALL available information: email SUBJECT, message BODY, and ATTACHMENTS (images/PDFs). Extract the 4 fields from any source or combination. Respond ONLY with valid JSON. [ES] DEBES revisar TODA la informacion: ASUNTO, CUERPO y ADJUNTOS. Extrae los 4 campos de cualquier fuente o combinacion. Responde UNICAMENTE con JSON. "
    "Eres un asistente especializado en extraer datos de pagos venezolanos. "
    "DEBES revisar TODA la informacion disponible: ASUNTO del mensaje, CUERPO del mensaje y ADJUNTOS (imagenes/PDFs); extrae los datos de cualquiera de estas fuentes o de su combinacion. "
    "Puedes recibir UNA O MÁS de estas fuentes:\n"
    "1) El ASUNTO del correo electrónico (subject; a veces incluye referencia, monto o datos del pagador).\n"
    "2) El CUERPO del correo (texto plano o HTML convertido a texto).\n"
    "3) Una o más imágenes o PDFs (comprobantes: recibo bancario, captura de app, Pago Móvil, transferencia, USDT, etc.).\n\n"
    "Extrae estos 4 datos de CUALQUIERA de las fuentes (asunto, cuerpo, imágenes o combinación). "
    "El asunto a menudo contiene número de referencia, monto o identificación; úsalo si el cuerpo o la imagen no lo tienen. "
    "Si el mismo dato aparece en varias fuentes, puedes usar cualquiera (prefiere la imagen cuando sea claramente un comprobante). "
    "Responde ÚNICAMENTE con el JSON sin texto adicional:\n"
    "{\n"
    "  \"fecha_pago\": \"...\",\n"
    "  \"cedula\": \"...\",\n"
    "  \"monto\": \"...\",\n"
    "  \"numero_referencia\": \"...\"\n"
    "}\n\n"
    "REGLAS POR CAMPO (aplican tanto al leer texto como imágenes):\n\n"
    "CEDULA (puede extraerse del ASUNTO, del CUERPO o de la IMAGEN):\n"
    "- Formato: V, E o J (y opcionalmente G) seguido de guion y números. Ejemplo en comprobante: DP:V-015989899 → cédula normalizada: V15989899.\n"
    "- Reglas: (1) Ignorar siempre el guión. (2) NUNCA tomar en cuenta ceros después de la letra; quitar ceros a la izquierda del número. V-015989899 = V15989899; V-0025677920 = V25677920.\n"
    "- En asunto/cuerpo busca: 'cédula', 'C.I.', 'RIF', 'DP:', 'V-', 'E-', 'J-', 'identificación', 'depositante'.\n"
    "- En imagen busca etiquetas: 'DP:V-', 'Cédula Dep.', 'C.I.', 'RIF'.\n"
    "- Devuelve tipo + dígitos sin guión y sin ceros a la izquierda (ej: 'V-015989899' → 'V15989899'). Si hay varias cédulas, la del PAGADOR/DEPOSITANTE.\n\n"
    "MONTO:\n"
    "- Bolívares (Bs, Bs., BsS) o dólares/divisas. Equivalencia: USDT = Dólares = USD = $. Cuando el comprobante indique USDT, Dólares, $ o USD, usa moneda 'USD' y monto en dólares. Ejemplos: '142.00 USD', '80000.00 Bs'.\n"
    "- En texto busca: 'monto', 'depósito', 'cantidad', 'total', 'importe', 'pagado', 'abono'.\n"
    "- Formato Bs: punto miles, coma decimal; normalizar a '80000.00 Bs'.\n\n"
    "NUMERO_REFERENCIA:\n"
    "- BNC: 'Ref:'; Mercantil: 'Serial:'; Banesco: 'Operación:'; genérico: 'referencia', 'operación', 'código', 'comprobante'.\n"
    "- Devuelve SOLO el número o código, sin la etiqueta. En texto busca frases como 'ref:', 'referencia nro', 'número de operación'.\n\n"
    "FECHA_PAGO:\n"
    "- Fecha de la operación/transacción en cualquier formato (dd/mm/yyyy, yyyy-mm-dd, 'DD MAR YYYY'). En asunto/cuerpo busca 'fecha', 'día', 'transacción'.\n\n"
    "Usa 'NA' solo cuando el dato NO aparezca en ninguna de las fuentes (asunto, cuerpo, imágenes). "
    "Si solo recibes asunto y/o cuerpo (sin imagen), extrae del texto. Si solo recibes imagen(es), extrae de la(s) imagen(es). "
    "No inventes datos. Si el contenido no es un comprobante ni un mensaje de pago (solo logo, firma, publicidad), devuelve los cuatro campos con 'NA'. "
    "FORMATO: Responde ÚNICAMENTE con un objeto JSON válido, sin texto antes ni después, sin markdown (no uses ```json). Responde SOLO el JSON."
)


def _build_image_part(file_content: bytes, filename: str, mime: str):
    """
    Convierte bytes en un Part de google.genai.
    Para imágenes: pasa por PIL para normalizar (JPEG). Para PDFs: bytes directos.
    """
    from google.genai import types as _gtypes
    is_pdf = mime == "application/pdf" or filename.lower().endswith(".pdf")
    if is_pdf:
        return _gtypes.Part.from_bytes(data=file_content, mime_type=mime)
    try:
        from PIL import Image as _PIL
        img = _PIL.open(io.BytesIO(file_content))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        logger.warning("[PAGOS_GMAIL] Gemini usando PIL→JPEG para %s", filename)
        return _gtypes.Part.from_bytes(data=buf.getvalue(), mime_type="image/jpeg")
    except Exception as pil_err:
        logger.warning("[PAGOS_GMAIL] PIL falló (%s), bytes crudos para %s", pil_err, filename)
        return _gtypes.Part.from_bytes(data=file_content, mime_type=mime)


def _gemini_client(key: str):
    from google import genai
    return genai.Client(api_key=key)


def extract_payment_data(
    file_content: Optional[bytes] = None,
    filename: Optional[str] = None,
    body_text: Optional[str] = None,
    subject: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Dict[str, str]:
    """
    Extrae fecha_pago, cedula, monto, numero_referencia de asunto, cuerpo, imagen/PDF o combinación.
    - subject: asunto del correo (opcional; a menudo trae referencia, monto o identificación).
    - body_text: cuerpo del correo en texto plano (opcional).
    - file_content + filename: imagen o PDF (comprobante).
    - Si solo hay texto (asunto/cuerpo), extrae del texto. Si hay imagen(es), puede combinar todas las fuentes.
    """
    key = api_key or getattr(settings, "GEMINI_API_KEY", None)
    if not key:
        logger.warning(
            "[CONFIG] GEMINI_API_KEY no configurado. Configure la variable de entorno GEMINI_API_KEY "
            "(obtener en https://aistudio.google.com/apikey). "
            "El pipeline seguirá guardando filas con 'NA' en los campos extraídos."
        )
        return _empty_result(PAGOS_NA)
    has_text = bool((subject and subject.strip()) or (body_text and body_text.strip()))
    if not file_content and not has_text:
        return _empty_result(PAGOS_NA)
    model_name = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
    contents: list = [GEMINI_PROMPT]
    text_parts: list = []
    if subject and subject.strip():
        text_parts.append("--- Asunto del correo ---\n" + subject.strip()[:2000])
    if body_text and body_text.strip():
        text_parts.append("--- Cuerpo del correo ---\n\n" + body_text.strip()[:12000])
    if text_parts:
        contents.append("\n\n".join(text_parts))
    image_part = None
    if file_content and filename:
        mime = get_mime_type(filename)
        image_part = _build_image_part(file_content, filename, mime)
        contents.append(image_part)
        logger.warning(
            "[PAGOS_GMAIL] Gemini → archivo=%s modelo=%s tamaño=%d bytes%s",
            filename, model_name, len(file_content),
            " + asunto/cuerpo" if has_text else "",
        )
    else:
        logger.warning(
            "[PAGOS_GMAIL] Gemini → solo asunto/cuerpo (sin imagen) modelo=%s%s",
            model_name, " asunto+cuerpo" if (subject and body_text) else "",
        )
    try:
        from google.genai import types
        client = _gemini_client(key)
        last_error = None
        for attempt in range(GEMINI_RATE_LIMIT_MAX_RETRIES + 1):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(temperature=0.1),
                )
                text = ""
                try:
                    text = (response.text or "").strip()
                except Exception as text_err:
                    candidates = getattr(response, "candidates", [])
                    finish_reasons = [str(getattr(c, "finish_reason", "?")) for c in candidates]
                    safety_ratings = []
                    for c in candidates:
                        for r in getattr(c, "safety_ratings", []):
                            safety_ratings.append(f"{r.category}={r.probability}")
                    logger.warning(
                        "[PAGOS_GMAIL] Gemini respuesta bloqueada/vacía para %s: %s | finish_reasons=%s | safety=%s",
                        filename or "cuerpo", text_err, finish_reasons, safety_ratings,
                    )
                    return _empty_result(f"blocked: {text_err}")

                logger.warning("[PAGOS_GMAIL] Gemini raw(%s): %s", filename or "cuerpo", text[:400] if text else "(VACÍO)")
                result = _parse_gemini_json(text)
                all_na = all(v == PAGOS_NA for v in result.values())
                if all_na:
                    logger.warning("[PAGOS_GMAIL] Gemini TODO NA para %s — respuesta: %s", filename or "cuerpo", text[:300])
                else:
                    logger.warning(
                        "[PAGOS_GMAIL] Gemini OK: fecha=%s cedula=%s monto=%s ref=%s",
                        result.get("fecha_pago"), result.get("cedula"),
                        result.get("monto"), result.get("numero_referencia"),
                    )
                return result
            except Exception as e:
                last_error = e
                # Reintentos para 429 (rate limit)
                if _is_rate_limit_error(e) and attempt < GEMINI_RATE_LIMIT_MAX_RETRIES:
                    delay = _extract_retry_seconds(e)
                    logger.warning("[PAGOS_GMAIL] Gemini 429 (cuota), reintento en %ds (%d/%d)", delay, attempt + 1, GEMINI_RATE_LIMIT_MAX_RETRIES + 1)
                    time.sleep(delay)
                # Reintentos para 503 (server unavailable / high demand)
                elif _is_server_error_503(e) and attempt < GEMINI_SERVER_ERROR_MAX_RETRIES:
                    delay = GEMINI_SERVER_ERROR_RETRY_DELAY + (attempt * 5)  # Backoff: 15s, 20s, 25s, 30s
                    logger.warning("[PAGOS_GMAIL] Gemini 503 (high demand), reintento en %ds (%d/%d)", delay, attempt + 1, GEMINI_SERVER_ERROR_MAX_RETRIES + 1)
                    time.sleep(delay)
                else:
                    raise
        return _empty_result(str(last_error))
    except Exception as e:
        logger.exception("Gemini extract_payment_data: %s", e)
        return _empty_result(str(e))


def _pagos_gmail_four_fields_complete(fields: Dict[str, str]) -> bool:
    """True solo si las cuatro columnas tienen valor real (no vacio ni NA)."""
    for k in ("fecha_pago", "cedula", "monto", "numero_referencia"):
        s = (fields.get(k) or "").strip()
        if not s or s.upper() == PAGOS_NA:
            return False
    return True


def _email_cliente_gemini_valido(s: str) -> bool:
    t = (s or "").strip()
    if not t or t.upper() == PAGOS_NA:
        return False
    if "@" not in t:
        return False
    local, _, domain = t.partition("@")
    if not local.strip() or not domain.strip() or "." not in domain:
        return False
    return True


def _pagos_gmail_format_c_complete(fields: Dict[str, str]) -> bool:
    """Formato C: monto, referencia, email_cliente reales; fecha y cedula deben NA."""
    fp = (fields.get("fecha_pago") or "").strip().upper()
    ce = (fields.get("cedula") or "").strip().upper()
    if fp != PAGOS_NA or ce != PAGOS_NA:
        return False
    for k in ("monto", "numero_referencia"):
        s = (fields.get(k) or "").strip()
        if not s or s.upper() == PAGOS_NA:
            return False
    if not _email_cliente_gemini_valido((fields.get("email_cliente") or "").strip()):
        return False
    return True


def _parse_formato_y_pagos_json(
    text: str,
    remitente_from_header: Optional[str] = None,
) -> Tuple[PagosGmailFormato, Dict[str, str]]:
    empty = _empty_result()
    try:
        json_str = _find_json_object(text)
        if not json_str:
            m = re.search(r"\{[^{}]*\}", text, re.DOTALL)
            json_str = m.group(0) if m else None
        if not json_str:
            return "ninguno", empty.copy()
        data = json.loads(json_str)
        fmt_raw = str(data.get("formato", "")).strip().upper()
        if fmt_raw == "A":
            fmt: PagosGmailFormato = "A"
        elif fmt_raw == "B":
            fmt = "B"
        elif fmt_raw == "C":
            fmt = "C"
        else:
            fmt = "ninguno"
        fields = {
            "fecha_pago": _normalize_to_na(data.get("fecha_pago", PAGOS_NA)),
            "cedula": _normalize_to_na(data.get("cedula", PAGOS_NA)),
            "monto": _normalize_to_na(data.get("monto", PAGOS_NA)),
            "numero_referencia": _normalize_to_na(data.get("numero_referencia", PAGOS_NA)),
            "email_cliente": _normalize_email_cliente_pagos_gmail(
                data.get("email_cliente", PAGOS_NA)
            ),
            "banco": _normalize_banco_gemini_field(data.get("banco", PAGOS_NA)),
        }
        na_fields = {
            "fecha_pago": PAGOS_NA,
            "cedula": PAGOS_NA,
            "monto": PAGOS_NA,
            "numero_referencia": PAGOS_NA,
            "email_cliente": PAGOS_NA,
            "banco": PAGOS_NA,
        }
        if fmt == "ninguno":
            return fmt, na_fields.copy()
        if fmt == "C":
            em0 = (fields.get("email_cliente") or "").strip()
            if not _email_cliente_gemini_valido(em0) and (remitente_from_header or "").strip():
                cand = extract_sender_email(remitente_from_header) or remitente_from_header.strip()
                if _email_cliente_gemini_valido(cand):
                    fields["email_cliente"] = _normalize_email_cliente_pagos_gmail(cand)
            if not _pagos_gmail_format_c_complete(fields):
                return "ninguno", na_fields.copy()
            fields["banco"] = PAGOS_NA
            return fmt, fields
        if not _pagos_gmail_four_fields_complete(fields):
            return "ninguno", na_fields.copy()
        fields["email_cliente"] = PAGOS_NA
        return fmt, fields
    except (json.JSONDecodeError, TypeError):
        return "ninguno", empty.copy()


def classify_and_extract_pagos_gmail_attachment(
    file_content: bytes,
    filename: str,
    api_key: Optional[str] = None,
    remitente_correo_header: Optional[str] = None,
) -> Tuple[PagosGmailFormato, Dict[str, str]]:
    """
    Clasifica el comprobante en formato A (RAPI-CREDIT terminal), B (BNC), C (Binance Pay) o ninguno,
    y extrae campos desde el archivo. Formato C puede usar remitente_correo_header (cabecera From)
    si el email del destinatario no aparece en la captura Binance.
    """
    key = api_key or getattr(settings, "GEMINI_API_KEY", None)
    if not key:
        logger.warning("[PAGOS_GMAIL] GEMINI_API_KEY no configurado; formato=ninguno")
        return "ninguno", _empty_result(PAGOS_NA)
    mime = get_mime_type(filename)
    image_part = _build_image_part(file_content, filename, mime)
    model_name = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
    contents: list = [GEMINI_PAGOS_GMAIL_FORMATO_Y_EXTRACCION]
    rf = (remitente_correo_header or "").strip()
    if rf:
        contents.append(
            "CONTEXTO_REMITE: "
            + rf
            + "\n(Solo formato C / Binance Pay: si no lees el email del destinatario en la captura, "
            "usa la direccion de correo de esta linea como email_cliente en el JSON.)\n"
        )
    contents.append(image_part)
    try:
        from google.genai import types
        client = _gemini_client(key)
        last_error = None
        for attempt in range(GEMINI_RATE_LIMIT_MAX_RETRIES + 1):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(temperature=0.1),
                )
                text = ""
                try:
                    text = (response.text or "").strip()
                except Exception as text_err:
                    logger.warning(
                        "[PAGOS_GMAIL] Gemini formato+extraccion bloqueada/vacia: %s",
                        text_err,
                    )
                    return "ninguno", _empty_result(f"blocked: {text_err}")
                fmt, fields = _parse_formato_y_pagos_json(
                    text, remitente_from_header=remitente_correo_header
                )
                if fmt not in PAGOS_GMAIL_FORMATOS_PLANTILLA:
                    fmt = "ninguno"
                    fields = {
                        "fecha_pago": PAGOS_NA,
                        "cedula": PAGOS_NA,
                        "monto": PAGOS_NA,
                        "numero_referencia": PAGOS_NA,
                        "email_cliente": PAGOS_NA,
                        "banco": PAGOS_NA,
                    }
                logger.info(
                    "[PAGOS_GMAIL] Gemini formato=%s fecha=%s cedula=%s monto=%s ref=%s email=%s banco=%s",
                    fmt,
                    fields.get("fecha_pago"),
                    fields.get("cedula"),
                    fields.get("monto"),
                    fields.get("numero_referencia"),
                    fields.get("email_cliente"),
                    fields.get("banco"),
                )
                return fmt, fields
            except Exception as e:
                last_error = e
                if _is_rate_limit_error(e) and attempt < GEMINI_RATE_LIMIT_MAX_RETRIES:
                    delay = _extract_retry_seconds(e)
                    logger.warning(
                        "[PAGOS_GMAIL] Gemini 429 formato+extraccion, reintento en %ds",
                        delay,
                    )
                    time.sleep(delay)
                elif _is_server_error_503(e) and attempt < GEMINI_SERVER_ERROR_MAX_RETRIES:
                    delay = GEMINI_SERVER_ERROR_RETRY_DELAY + (attempt * 5)
                    logger.warning(
                        "[PAGOS_GMAIL] Gemini 503 formato+extraccion, reintento en %ds",
                        delay,
                    )
                    time.sleep(delay)
                else:
                    raise
        return "ninguno", _empty_result(str(last_error))
    except Exception as e:
        logger.exception("Gemini classify_and_extract_pagos_gmail_attachment: %s", e)
        return "ninguno", _empty_result(str(e))


# ── Cobranza ────────────────────────────────────────────────────────────────

COBRANZA_NA = "NA"
GEMINI_COBRANZA_PROMPT = (
    "Esta imagen es una papeleta de depósito, recibo de pago o comprobante bancario. "
    "Extrae exactamente estos campos en formato JSON (usa 'NA' si no encuentras el dato): "
    '"fecha_deposito" (fecha del depósito, formato dd/mm/yyyy o yyyy-mm-dd), '
    '"nombre_banco" (nombre del banco, institución financiera, o "Recibo"/recibo/REcibo si solo aparece esa palabra), '
    '"numero_deposito" (número de depósito, referencia o transacción, muchos dígitos), '
    '"numero_documento" (número de documento, recibo o comprobante de venta), '
    '"cantidad" (monto total en números, ej. 150.00 o 1.234,56), '
    '"aceptable" (true si el documento es claramente un comprobante de pago legible; false si está ilegible o no es comprobante). '
    "Responde SOLO con el JSON, sin texto adicional ni markdown."
)


def extract_cobranza_from_image(
    image_bytes: bytes,
    filename: str = "image.jpg",
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Toma la imagen (papeleta/comprobante) y extrae información de cobranza con Gemini.
    """
    key = api_key or getattr(settings, "GEMINI_API_KEY", None)
    base_na: Dict[str, Any] = {
        "fecha_deposito": COBRANZA_NA,
        "nombre_banco": COBRANZA_NA,
        "numero_deposito": COBRANZA_NA,
        "numero_documento": COBRANZA_NA,
        "cantidad": COBRANZA_NA,
        "humano": "",
        "confianza_media": 0.0,
    }
    if not key or not str(key).strip():
        logger.warning("[COBRANZA] GEMINI_API_KEY no configurado.")
        return base_na
    model_name = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
    mime = get_mime_type(filename)
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=key)
        image_part = _build_image_part(image_bytes, filename, mime)
        safety = [
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
        ]
        last_error = None
        for attempt in range(GEMINI_RATE_LIMIT_MAX_RETRIES + 1):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[GEMINI_COBRANZA_PROMPT, image_part],
                    config=types.GenerateContentConfig(temperature=0.1, safety_settings=safety),
                )
                text = (response.text or "").strip()
                return _parse_cobranza_json(text)
            except Exception as e:
                last_error = e
                # Reintentos para 429 (rate limit)
                if _is_rate_limit_error(e) and attempt < GEMINI_RATE_LIMIT_MAX_RETRIES:
                    delay = _extract_retry_seconds(e)
                    logger.warning("[COBRANZA] Gemini 429, reintento en %ds (%d/%d)", delay, attempt + 1, GEMINI_RATE_LIMIT_MAX_RETRIES + 1)
                    time.sleep(delay)
                # Reintentos para 503 (server unavailable / high demand)
                elif _is_server_error_503(e) and attempt < GEMINI_SERVER_ERROR_MAX_RETRIES:
                    delay = GEMINI_SERVER_ERROR_RETRY_DELAY + (attempt * 5)  # Backoff: 15s, 20s, 25s, 30s
                    logger.warning("[COBRANZA] Gemini 503 (high demand), reintento en %ds (%d/%d)", delay, attempt + 1, GEMINI_SERVER_ERROR_MAX_RETRIES + 1)
                    time.sleep(delay)
                else:
                    raise
        return base_na
    except Exception as e:
        logger.exception("Gemini extract_cobranza_from_image: %s", e)
        return base_na


def check_gemini_available() -> Dict[str, Any]:
    """Verifica que la API key es válida y el modelo responde."""
    key = getattr(settings, "GEMINI_API_KEY", None)
    if not key or not str(key).strip():
        return {"ok": False, "error": "GEMINI_API_KEY no configurado"}
    model_name = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=key)
        last_error = None
        for attempt in range(GEMINI_RATE_LIMIT_MAX_RETRIES + 1):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents="Responde únicamente con la palabra OK, nada más.",
                    config=types.GenerateContentConfig(temperature=0.0),
                )
                text = (response.text or "").strip()
                if text:
                    return {"ok": True, "model": model_name, "response_preview": text[:50]}
                return {"ok": False, "error": "Gemini no devolvió texto"}
            except Exception as e:
                last_error = e
                # Reintentos para 429 (rate limit)
                if _is_rate_limit_error(e) and attempt < GEMINI_RATE_LIMIT_MAX_RETRIES:
                    delay = _extract_retry_seconds(e)
                    logger.warning("[PAGOS_GMAIL] Gemini 429 en health check, reintento en %ds (%d/%d)", delay, attempt + 1, GEMINI_RATE_LIMIT_MAX_RETRIES + 1)
                    time.sleep(delay)
                # Reintentos para 503 (server unavailable / high demand)
                elif _is_server_error_503(e) and attempt < GEMINI_SERVER_ERROR_MAX_RETRIES:
                    delay = GEMINI_SERVER_ERROR_RETRY_DELAY + (attempt * 5)  # Backoff: 15s, 20s, 25s, 30s
                    logger.warning("[PAGOS_GMAIL] Gemini 503 (high demand) en health check, reintento en %ds (%d/%d)", delay, attempt + 1, GEMINI_SERVER_ERROR_MAX_RETRIES + 1)
                    time.sleep(delay)
                else:
                    raise
        return {"ok": False, "error": str(last_error)}
    except Exception as e:
        logger.exception("Gemini check_gemini_available: %s", e)
        return {"ok": False, "error": str(e)}


# ── Helpers internos ────────────────────────────────────────────────────────

def _find_json_object(text: str) -> Optional[str]:
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```\s*$", "", text.strip())
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    quote = None
    for i in range(start, len(text)):
        c = text[i]
        if escape:
            escape = False
            continue
        if c == "\\" and in_string:
            escape = True
            continue
        if not in_string:
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
            elif c in ('"', "'"):
                in_string = True
                quote = c
        elif c == quote:
            in_string = False
    return None


def _normalize_banco_gemini_field(val: Any) -> str:
    """Campo banco en JSON Gemini (A/B); sin prefijos de _normalize_to_na."""
    if val is None:
        return PAGOS_NA
    s = str(val).strip()
    if not s or s.lower() in ("no encontrado", "n/a", "n.a.", "-", "—", "na"):
        return PAGOS_NA
    return s[:200]


def _normalize_email_cliente_pagos_gmail(val: Any) -> str:
    """
    Normaliza email_cliente sin el prefijo-ref de _normalize_to_na (evita cortar 'operaciones@...' -> 'es@...').
    """
    if val is None:
        return PAGOS_NA
    s = str(val).strip()
    if not s or s.lower() in ("no encontrado", "n/a", "n.a.", "-", "—", "na"):
        return PAGOS_NA
    return s


def _normalize_to_na(val: Any) -> str:
    if val is None:
        return PAGOS_NA
    s = str(val).strip()
    if not s or s.lower() in ("no encontrado", "n/a", "n.a.", "-", "—", "na"):
        return PAGOS_NA
    s = re.sub(
        r"^(Ref|Serial|Operaci[oó]n|N[°º]?\s*de\s*(referencia|operaci[oó]n|transferencia)|"
        r"ID\s*de\s*orden|N[°º]mero\s*de\s*referencia|NÚMERO\s*DE\s*REFERENCIA|"
        r"Nro\.?\s*de\s*referencia|C[oó]digo\s*de\s*operaci[oó]n|Nro\.?\s*comprobante)"
        r"\s*[:\-]?\s*",
        "", s, flags=re.IGNORECASE,
    ).strip()
    s = re.sub(r"\s*\(.*?\)\s*$", "", s).strip()
    return s if s else PAGOS_NA


def _parse_gemini_json(text: str) -> Dict[str, str]:
    default = {"fecha_pago": PAGOS_NA, "cedula": PAGOS_NA, "monto": PAGOS_NA, "numero_referencia": PAGOS_NA}
    try:
        json_str = _find_json_object(text)
        if not json_str:
            match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
            json_str = match.group(0) if match else None
        if json_str:
            data = json.loads(json_str)
            return {
                "fecha_pago": _normalize_to_na(data.get("fecha_pago", default["fecha_pago"])),
                "cedula": _normalize_to_na(data.get("cedula", default["cedula"])),
                "monto": _normalize_to_na(data.get("monto", default["monto"])),
                "numero_referencia": _normalize_to_na(data.get("numero_referencia", default["numero_referencia"])),
            }
    except json.JSONDecodeError:
        pass
    return default.copy()


def _empty_result(reason: str = "") -> Dict[str, str]:
    if reason:
        logger.debug("[PAGOS_GMAIL] Gemini sin datos: %s", reason)
    return {
        "fecha_pago": PAGOS_NA,
        "cedula": PAGOS_NA,
        "monto": PAGOS_NA,
        "numero_referencia": PAGOS_NA,
        "email_cliente": PAGOS_NA,
        "banco": PAGOS_NA,
    }


def _parse_cobranza_json(text: str) -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "fecha_deposito": COBRANZA_NA,
        "nombre_banco": COBRANZA_NA,
        "numero_deposito": COBRANZA_NA,
        "numero_documento": COBRANZA_NA,
        "cantidad": COBRANZA_NA,
        "humano": "",
        "confianza_media": 0.9,
    }
    try:
        json_str = _find_json_object(text)
        if not json_str:
            m = re.search(r"\{[^{}]*\}", text, re.DOTALL)
            json_str = m.group(0) if m else None
        if not json_str:
            return base
        data = json.loads(json_str)
        for k in ("fecha_deposito", "nombre_banco", "numero_deposito", "numero_documento", "cantidad"):
            v = data.get(k)
            if v is not None and str(v).strip():
                base[k] = str(v).strip()[:255] if k == "nombre_banco" else str(v).strip()[:100]
        if data.get("aceptable") is False:
            base["humano"] = "HUMANO"
        return base
    except (json.JSONDecodeError, TypeError):
        return base


def _is_rate_limit_error(exc: Exception) -> bool:
    msg = (getattr(exc, "message", "") or str(exc)) if exc else ""
    return "429" in msg or "quota" in msg.lower() or "rate" in msg.lower()


def _is_server_error_503(exc: Exception) -> bool:
    """Detecta errores 503 UNAVAILABLE (ServerError de Gemini por alta demanda)."""
    msg = (getattr(exc, "message", "") or str(exc)) if exc else ""
    return "503" in msg or "UNAVAILABLE" in msg or "high demand" in msg.lower()


def _extract_retry_seconds(exc: Exception) -> int:
    msg = (getattr(exc, "message", "") or str(exc)) if exc else ""
    m = re.search(r"retry\s+in\s+([\d.]+)\s*s", msg, re.IGNORECASE)
    if m:
        return max(1, int(float(m.group(1))))
    return GEMINI_RATE_LIMIT_RETRY_DELAY


# ── Cobros: comparar datos del formulario con la imagen del comprobante ─────

GEMINI_COMPARAR_PROMPT_PREFIX = """Eres un revisor de comprobantes de pago. Recibes:
1) Los datos que una persona ingresó manualmente en un formulario (cada campo listado abajo).
2) Una imagen o PDF del comprobante de pago (recibo bancario, transferencia, Pago Móvil, etc.).

REGLAS DEL VALIDADOR DE CÉDULA (aplicar siempre; alineado con el sistema):
- Tipos válidos: solo V, E, G o J (cédula venezolana). RIF puede verse como J o E + dígitos.
- Ejemplo en comprobante: DP:V-015989899 → cédula a usar: V15989899. (1) Ignorar el guión. (2) NUNCA tomar en cuenta ceros después de la letra (ej. V): quitar siempre los ceros a la izquierda del número.
- Formato normalizado: tipo (una letra) + entre 6 y 11 dígitos sin ceros a la izquierda. V-015989899 = V15989899; V-0025677920 = V25677920; 0025677920 con tipo V = V25677920.
- Al comparar: ignora guión, espacios y ceros a la izquierda del número. Solo cuenta que el tipo (V/E/G/J) sea el mismo y que el número (sin ceros después de la letra) sea el mismo.
- NO incluyas "Cédula" en comentario si la única diferencia es: ceros a la izquierda, guión o espacios. Solo marca Cédula cuando tipo o número (normalizado) sean realmente distintos.

NÚMERO DE OPERACIÓN (igual que Serial / Referencia en el comprobante):
- En el formulario el campo se llama "Número de operación". En el comprobante puede aparecer con OTRO nombre: "Serial", "Serial:", "Nº operación", "Número de operación", "Referencia", "Nº de referencia", "Código", "Número de transacción", etc. Todos son el mismo concepto: el número o código que identifica la transacción. Si en el recibo ves "Serial: 740087401612580", ese valor 740087401612580 ES el número de operación. Compáralo con lo que la persona ingresó en el formulario; si los dígitos coinciden (ignorando espacios o guiones), COINCIDE. No marques "Nº operación" como divergencia solo porque en el comprobante dice "Serial" en vez de "Número de operación".

EXCEPCIÓN BANCO = BINANCE (aplicar siempre y solo en este caso):
- Si la columna Banco (institucion_financiera) es BINANCE (o Binance), IGNORAR siempre el error de fecha. En el formato de imagen para Banco = BINANCE no hay fecha que comprobar; no incluyas "Fecha pago" en el comentario por diferencia de fecha cuando el banco sea BINANCE.

REGLA CRÍTICA — MONEDA USDT / USD (obligatoria; no negociable):
- En este sistema USDT y USD son LA MISMA moneda para validar el comprobante: dólares / stablecoin en USD / Tether / US$ / símbolo $ / texto "Dólares" en el recibo = equivalente a USD.
- Si el formulario indica USD y el comprobante muestra USDT (o al revés), o uno dice "USDT" y el otro "USD" o "$", NO hay divergencia de Moneda si el monto numérico coincide.
- NUNCA pongas "Moneda" en comentario ni marques coincide_exacto=false únicamente por diferencia de etiqueta USDT vs USD vs $ vs "Dólares". Eso NO es error: debe contar como COINCIDENCIA de moneda.
- coincide_exacto debe ser true si todos los demás campos verificables coinciden y el único "desacuerdo" sería USDT frente a USD (o sinónimos de dólares).

INSTRUCCIONES:

Paso 1 — Extraer de la imagen: Lee el comprobante y extrae con precisión estos datos (los que aparezcan):
- fecha_pago: fecha de la operación/transacción que aparece en el comprobante (día, mes y año). Puede estar en cualquier formato (dd/mm/yyyy, yyyy-mm-dd, texto, etc.). Este valor se comparará con la fecha que la persona ingresó en el formulario.
- institucion_financiera: nombre del banco o entidad (ej. Banesco, Mercantil, BNC, BDV, Pago Móvil). Si en el comprobante solo aparece la palabra Recibo/Recibos (ej. recibo, REcibo, recibos) sin nombre de banco, usa "Recibo" como institucion_financiera; es un valor válido en el criterio Bancos/banco. Para comparar Banco, Recibo y Recibos se consideran equivalentes.
- numero_operacion: es el número/código de la transacción. En el comprobante puede aparecer como "Serial", "Serial:", "Nº operación", "Referencia", "Número de referencia", "Código de operación", etc. Extrae los dígitos (y letras si los hay) de ese campo; ese valor es el numero_operacion para comparar con el formulario.
- monto: cantidad pagada (número; puede estar en Bs, USD, USDT, etc.).
- moneda: BS o USD. Regla: USDT = Dólares = USD = $; si el comprobante muestra USDT, Dólares, $ o USD, devuelve moneda 'USD'.
- cedula_pagador: cédula de quien paga/deposita. En el comprobante puede aparecer como "DP:V-015989899", "Cédula Dep.:", "Nro. de Cédula", "DP:", "C.I.", etc. Reglas: ignorar guión; NUNCA tomar en cuenta ceros después de la letra (ej. V-015989899 → V15989899). Normaliza a tipo (V, E, G o J) + dígitos sin guión y sin ceros a la izquierda; si solo ves dígitos (ej. 015989899), antepón V. Resultado para comparar: tipo + número sin ceros a la izquierda (ej. V15989899).

Paso 2 — Comparar campo por campo: Para cada dato extraído de la imagen, compáralo con el valor que la persona ingresó en el formulario (listado abajo). Reglas:
- Fecha pago: La fecha del formulario debe coincidir con la fecha de la operación en la imagen. Si difiere, es divergencia (incluir "Fecha pago" en comentario). EXCEPCIÓN: si Banco = BINANCE (o Binance), NO comparar fecha ni incluir "Fecha pago" en comentario; en comprobantes BINANCE no hay fecha que comprobar. Ignorar solo el formato (ej. 10/03/2026 vs 2026-03-10 = misma fecha).
- Institución: mismo banco o entidad (sinónimos o nombre abreviado = válido). Recibo/Recibos (y variaciones de mayúsculas/minúsculas) se consideran el mismo valor (coinciden entre sí).
- Número de operación: el formulario tiene "numero_operacion"; en el comprobante puede estar como "Serial", "Referencia", "Nº operación", etc. Es el mismo dato. Compara los dígitos/código; si coinciden (ignorar espacios o guiones intermedios), COINCIDE. No marques divergencia solo porque la etiqueta en el recibo diga "Serial" en vez de "Número de operación".
- Monto y moneda: mismo valor numérico. Para moneda: BS/Bs/bolívares = misma familia; USD/USDT/US$/Dólares/$/Tether = misma familia (USDT=USD siempre). No marques columna Moneda solo por USDT vs USD.
- Cédula: aplicar las REGLAS DEL VALIDADOR DE CÉDULA anteriores. Ejemplo: comprobante DP:V-015989899 → normalizado V15989899 (ignorar guión; nunca ceros después de la letra). Comparar tipo (V/E/G/J) y número sin ceros a la izquierda. Si en imagen ves V-015989899 o 015989899 y en formulario V15989899 → COINCIDE. Solo es divergencia si el tipo o el número (normalizado) son distintos. Verifica haber quitado guión y ceros a la izquierda antes de marcar Cédula en comentario.

Paso 3 — Decidir:
- coincide_exacto = true SOLO si TODOS los campos que se pueden verificar en la imagen coinciden con lo ingresado en el formulario (para cédula: mismo tipo y mismo número normalizado sin ceros a la izquierda). Si la cédula no aparece en el comprobante, no la uses para marcar false. Si Banco = BINANCE, no uses Fecha pago para marcar false (en BINANCE no hay fecha que comprobar). USDT vs USD nunca impide coincide_exacto=true si el monto numérico y el resto coinciden.
- coincide_exacto = false si CUALQUIER campo extraído de la imagen NO coincide con el formulario (comparando valores normalizados), o si no puedes leer con claridad algún dato necesario. No marques false por cédula si la única diferencia es guión, espacios o ceros a la izquierda en el número.
- comentario: si coincide_exacto = false, es OBLIGATORIO indicar SOLO los nombres de las columnas que no coinciden, separados por coma. Usa EXACTAMENTE estos nombres: Cédula, Banco, Fecha pago, Nº operación, Monto, Moneda. Sin explicaciones. Ejemplo: "Monto, Fecha pago". Si coincide_exacto = true, deja comentario vacío o "".

Responde ÚNICAMENTE con un JSON válido, sin markdown ni texto antes o después:
{"coincide_exacto": true o false, "requiere_revision_humana": true o false, "comentario": "solo nombres de columnas separados por coma: Cédula, Banco, Fecha pago, Nº operación, Monto, Moneda"}
"""


def _comentario_solo_columna_moneda(comentario: str) -> bool:
    """True si el comentario de divergencia es únicamente la columna Moneda (p. ej. 'Moneda', 'Moneda, Moneda')."""
    if not comentario or not str(comentario).strip():
        return False
    tokens = []
    for t in str(comentario).split(","):
        s = t.strip().lower().rstrip(".;:")
        if s:
            tokens.append(s)
    return bool(tokens) and all(t == "moneda" for t in tokens)


def _is_recibo_alias(value: Any) -> bool:
    """True cuando el texto representa Recibo/Recibos (ignorando mayúsculas y espacios)."""
    if value is None:
        return False
    normalized = str(value).strip().lower()
    return normalized in {"recibo", "recibos"}


def compare_form_with_image(
    form_data: Dict[str, Any],
    image_bytes: bytes,
    filename: str = "comprobante.jpg",
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compara los datos ingresados en el formulario con lo que muestra la imagen del comprobante.
    Usa el mismo cliente Gemini del sistema (_gemini_client + GEMINI_API_KEY y GEMINI_MODEL).
    Retorna: {"coincide_exacto": bool, "requiere_revision_humana": bool, "comentario": str}
    Si coincide_exacto es True → se puede aprobar automáticamente. Si no → en_revision humana.
    
    Implementa caché en memoria (24h TTL) para evitar re-procesar comprobantes duplicados.
    """
    from app.services.pagos_gmail.gemini_cache import cache_get, cache_set
    
    key = api_key or getattr(settings, "GEMINI_API_KEY", None)
    default_result = {
        "coincide_exacto": False,
        "requiere_revision_humana": True,
        "comentario": "No se pudo verificar (Gemini no configurado o error).",
    }
    if not key or not str(key).strip():
        logger.warning("[COBROS] GEMINI_API_KEY no configurado para comparar formulario vs imagen.")
        return default_result
    
    cached_result = cache_get(image_bytes, form_data)
    if cached_result:
        logger.info("[COBROS] Gemini: resultado desde caché (SHA256 imagen + form_data)")
        return cached_result
    # Cédula: formato estándar sin guión (tipo + dígitos); normalizar número sin ceros a la izquierda para comparar
    tipo_c = (form_data.get("tipo_cedula") or "").strip().upper()
    num_c = (form_data.get("numero_cedula") or "").strip()
    num_sin_ceros = num_c.lstrip("0") or "0"  # 0025677920 -> 25677920; 0 -> 0
    cedula_estandar = f"{tipo_c}{num_c}" if (tipo_c and num_c) else (form_data.get("tipo_cedula") or "") + (form_data.get("numero_cedula") or "")
    _fm = (form_data.get("moneda") or "BS").strip().upper()
    _fm_label = "USD" if _fm in ("USD", "USDT") else _fm
    text_data = (
        "Valores ingresados manualmente en el formulario (compara cada uno con lo que leas en la imagen):\n"
        f"- fecha_pago: {form_data.get('fecha_pago')}\n"
        f"- institucion_financiera: {form_data.get('institucion_financiera')}\n"
        f"- numero_operacion: {form_data.get('numero_operacion')}\n"
        f"- monto: {form_data.get('monto')} {_fm_label}"
        + (" (USDT equivale a USD; si el comprobante dice USDT y aquí USD, es la misma moneda)\n" if _fm_label == "USD" else "\n")
        + f"- cedula (tipo + número): {cedula_estandar}. Ejemplo en comprobante: DP:V-015989899 → V15989899 (ignorar guión; nunca contar ceros después de la letra). Número normalizado para comparar: {tipo_c or 'V'}{num_sin_ceros}. Si tipo y ese número coinciden, NO incluyas Cédula en comentario.\n"
    )
    prompt = GEMINI_COMPARAR_PROMPT_PREFIX + "\n\n" + text_data
    model_name = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
    mime = get_mime_type(filename)
    try:
        from google import genai
        from google.genai import types
        client = _gemini_client(key)
        image_part = _build_image_part(image_bytes, filename, mime)
        last_error = None
        # Determinar número máximo de reintentos según si es 503 o 429
        max_retries = GEMINI_RATE_LIMIT_MAX_RETRIES
        for attempt in range(GEMINI_RATE_LIMIT_MAX_RETRIES + 1):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[prompt, image_part],
                    config=types.GenerateContentConfig(temperature=0.1),
                )
                text = (response.text or "").strip()
                json_str = _find_json_object(text)
                if not json_str:
                    m = re.search(r"\{[^{}]*\}", text, re.DOTALL)
                    json_str = m.group(0) if m else None
                if json_str:
                    data = json.loads(json_str)
                    comentario = str(data.get("comentario", ""))[:500]
                    coincide = bool(data.get("coincide_exacto"))
                    # Filtro: si Gemini reporta divergencia solo por guión/formato en cédula, ignorar (falsa alarma)
                    if not coincide and comentario:
                        lower = comentario.lower()
                        solo_cedula_formato = (
                            ("cédula" in lower or "cedula" in lower)
                            and ("v-" in lower or "guión" in lower or "guion" in lower or "prefijo" in lower or "ceros" in lower or "formato" in lower)
                            and not any(k in lower for k in ("monto", "fecha", "operación", "operacion", "banco", "institución", "numero", "moneda"))
                        )
                        if solo_cedula_formato:
                            coincide = True
                            comentario = ""
                            logger.info("[COBROS] Gemini: divergencia solo por formato cédula; ignorada.")
                    # USDT = USD: si solo lista "Moneda" y el pago es en dólares, no rechazar
                    if not coincide and comentario:
                        form_mon = (form_data.get("moneda") or "BS").strip().upper()
                        form_mon_norm = "USD" if form_mon in ("USD", "USDT") else form_mon
                        if form_mon_norm == "USD" and _comentario_solo_columna_moneda(comentario):
                            coincide = True
                            comentario = ""
                            logger.info("[COBROS] Gemini: divergencia solo Moneda (USDT=USD); ignorada.")
                    # Banco Recibo/Recibos: tratar como equivalentes para evitar falsos negativos.
                    if not coincide and comentario:
                        lower_comment = comentario.lower()
                        solo_banco = (
                            "banco" in lower_comment
                            and not any(
                                k in lower_comment
                                for k in ("cédula", "cedula", "fecha", "operación", "operacion", "monto", "moneda")
                            )
                        )
                        if solo_banco and _is_recibo_alias(form_data.get("institucion_financiera")):
                            coincide = True
                    comentario = ""
                    logger.info("[COBROS] Gemini: divergencia solo Banco con Recibo/Recibos; ignorada.")
                    result = {
                        "coincide_exacto": coincide,
                        "requiere_revision_humana": not coincide,
                        "comentario": comentario,
                    }
                    cache_set(image_bytes, form_data, result)
                    return result
                result = {
                    "coincide_exacto": coincide,
                    "requiere_revision_humana": not coincide,
                    "comentario": comentario,
                }
                cache_set(image_bytes, form_data, result)
                return result
            except Exception as e:
                last_error = e
                # Reintentos para 429 (rate limit)
                if _is_rate_limit_error(e) and attempt < GEMINI_RATE_LIMIT_MAX_RETRIES:
                    delay = _extract_retry_seconds(e)
                    logger.warning("[COBROS] Gemini 429 en comparar, reintento %d/%d en %ds", attempt + 1, GEMINI_RATE_LIMIT_MAX_RETRIES, delay)
                    time.sleep(delay)
                # Reintentos para 503 (server unavailable / high demand)
                elif _is_server_error_503(e) and attempt < GEMINI_SERVER_ERROR_MAX_RETRIES:
                    delay = GEMINI_SERVER_ERROR_RETRY_DELAY + (attempt * 5)  # Backoff: 15s, 20s, 25s, 30s
                    logger.warning("[COBROS] Gemini 503 (high demand) en comparar, reintento %d/%d en %ds", attempt + 1, GEMINI_SERVER_ERROR_MAX_RETRIES, delay)
                    time.sleep(delay)
                else:
                    raise
        return default_result
    except Exception as e:
        logger.exception("Gemini compare_form_with_image: %s", e)
        default_result["comentario"] = str(e)[:500]
        return default_result

