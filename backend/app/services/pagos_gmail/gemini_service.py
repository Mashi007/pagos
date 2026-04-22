"""
Gemini: enviar imagen o PDF, extraer datos de comprobantes.
Usa el paquete google-genai (google.genai) — sucesor de google-generativeai.
Configuración única para todo el sistema: GEMINI_API_KEY y GEMINI_MODEL (app.core.config.settings).

- Pagos (Gmail): fecha_pago, cedula, monto, numero_referencia (extract_payment_data).
- Cobranza (papeleta/informe): fecha_deposito, nombre_banco, etc. (extract_cobranza_from_image).
- Cobros (reporte público): comparar datos del formulario vs imagen del comprobante (compare_form_with_image).
- Cobros (escáner Infopagos, personal autenticado): extraer sugerencia de campos desde solo la imagen (extract_infopagos_campos_desde_comprobante).
  Cobros usa la misma API key y modelo que el resto del sistema; sin clave, los reportes van a en_revision.
"""
import io
import json
import logging
import re
import time
from datetime import date
from functools import lru_cache
from typing import Any, Dict, Literal, Optional, Tuple

GEMINI_RATE_LIMIT_RETRY_DELAY = 45
GEMINI_RATE_LIMIT_MAX_RETRIES = 2
GEMINI_SERVER_ERROR_RETRY_DELAY = 15  # Para 503 Server Unavailable
GEMINI_SERVER_ERROR_MAX_RETRIES = 4  # Máximo 4 reintentos para 503

from app.core.config import settings
from app.services.pagos_gmail.helpers import get_mime_type

logger = logging.getLogger(__name__)

PAGOS_NA = "NA"

PagosGmailFormato = Literal["A", "B", "C", "D", "NR", "ninguno"]

# Apéndice al prompt cuando scan_filter=error_email_rescan (re-lectura A/B con cédula en JSON).
GEMINI_PAGOS_GMAIL_MODO_ERROR_EMAIL_AB = """
MODO ESPECIAL — RE-ESCANEO (solo esta peticion; el backend usa scan_filter **error_email_rescan**):
  El hilo puede tener etiqueta Gmail **ERROR EMAIL** (p. ej. remitente sin match en clientes u otras reglas del backend). Aqui se pide **re-clasificar** solo con la **misma** logica visual de **Mercantil (A)** y **BNC (B)** que el prompt principal, con **exigencia maxima** de legibilidad.
  CALIDAD / NO INVENTAR: Si **fecha_pago**, **monto** o **numero_referencia** no son **100%** legibles en los pixeles (borroso, recorte severo, reflejo, compresion ilegible) -> **formato "ninguno"** y todos los campos "NA". No rellenes desde asunto ni cuerpo del correo.
  FORMATOS **A** y **B** — el campo JSON **"cedula"** **si** se evalua en este modo (excepcion al bloque REGLA CEDULA **solo** para esta peticion y solo si clasificas A o B):
    - Extrae la cedula del **depositante** **unicamente** desde el comprobante: **DP:V-** / **DP:E-** / **DP:J-** + digitos, **Cedula Dep.**, casillas **Nro. de Cédula** en papel Mercantil, etc.
    - Si **todos** los digitos son inequivocos, devuelve cadena con prefijo **V**, **E** o **J** en mayuscula + digitos sin puntos (ej. **V30145077**). Puedes leer desde linea DP con o sin guion entre letra y numeros.
    - Si hay **cualquier** duda en un digito, la zona esta tapada/sellada o no hay patron claro -> **"cedula":"ERROR"** (literal ERROR, sin comillas extra en JSON).
    - Si no devuelves A ni B (ninguno, C, D, NR), **"cedula"** debe ser **"NA"** como siempre.
  FORMATOS **C**, **D**, **NR** y **ninguno**: **"cedula":"NA"** (este modo no cambia la regla de cedula en C/D/NR).
"""

GEMINI_PAGOS_GMAIL_FORMATO_Y_EXTRACCION = """
Eres un clasificador estricto. Entrada: una sola imagen o PDF extraida del mensaje (incrustada en cuerpo, adjunto con nombre,
o comprobante dentro de un correo reenviado .eml). No uses asunto del correo ni texto del cuerpo para clasificar ni rellenar campos del JSON
salvo cuando este prompt autorice explicitamente otro criterio. La **cedula** jamas se obtiene del asunto, cuerpo, imagen ni PDF (REGLA CEDULA).
Si hay duda -> formato "ninguno" y los cuatro campos "NA". No inventes datos.

REGLA CEDULA (SISTEMA — obligatoria imagen 1, 2, 3 y 4 / formatos A, B, C, D, NR):
  NO extraigas, NO copies y NO infieras el **numero de cedula** (ni V-, E-, J-, CI, RIF, documento del depositante) desde:
    - imagen **embebida** en el HTML del correo (inline, CID, multipart related),
    - imagen **adjunta** (.jpg, .png, .webp, etc.),
    - **PDF** adjunto o pagina incrustada,
    - ningun otro **archivo binario** que te envien en esta peticion,
    - **cuerpo** del mensaje ni **asunto**.
  Da igual el origen Gmail (pegada en cuerpo vs adjunto vs reenvio .eml): la regla es la misma.
  En JSON el campo "cedula" debe ser SIEMPRE el literal **"NA"** para **imagen 1 (A)**, **imagen 2 (B)**, **imagen 3 (C)**, **imagen 4 (D)** y **NR**.
  El backend asigna la cedula real consultando la tabla clientes por el email del remitente (cabecera De / From).
  REGLA BACKEND — comparacion email (De / From) vs tabla `clientes` (misma regla para A, B, C, D y NR):
    (1) Comparar con `clientes.email` (predeterminado), trim y minusculas.
    (2) Si no coincide, comparar con `clientes.email_secundario` (correo 2) si no esta vacio.
    (3) Si no coincide ninguno, o si falla la consulta a la base de datos: la **columna Cedula** del Excel (export) quedara con el texto **ERROR EMAIL** y el backend aplicara en Gmail **solo** la etiqueta de usuario **ERROR EMAIL** (sin combinar con MERCANTIL/BNC/etc. en ese paso); el modelo no inventa cedula (no es tu tarea rellenar cedula).
  Puedes usar lineas DP:, Cedula Dep., casillas de cedula en papel, RIF depositante, etc. **solo** para **clasificar** plantilla (A vs B, etc.);
    **nunca** escribas esos digitos en el campo "cedula" del JSON.

ORIGEN EN GMAIL (embebida vs adjunta): misma regla en todos los casos.
  Cada peticion te envia UN solo binario (una imagen o un PDF). Ese binario puede proceder de:
    (a) adjunto clasico al mensaje,
    (b) imagen incrustada en el HTML del cuerpo (inline / CID / multipart related),
    (c) imagen detectada dentro del cuerpo sin filename util,
    (d) PDF adjunto o pagina de PDF, o trozo extraido de un .eml reenviado.
  **REGLA CEDULA** aplica igual en (a)-(d): **no** copies cedula del binario aunque sea embebida o adjunta.
  No importa el origen: si el contenido visual es plantilla A, B, C (Binance Pay) o D (BDV), clasifica igual. No descartes por "parece pegado en el correo" o "no es adjunto".
  Nombres genericos del sistema (inline-0.jpg, image.png, unnamed, parte sin titulo) NO son evidencia de ninguno; solo cuenta lo que se ve en los pixeles.
  Si ves chrome de cliente de correo (cabeceras, botones, fondo gris) alrededor pero el ticket o recibo BNC/RAPI es legible en el centro, ignora el marco y lee el comprobante.
  Si el binario es solo firma, logo, banner, avatar o recorte sin los datos de operacion, o el comprobante esta tan cortado que no puedes fecha/monto/referencia con certeza -> ninguno.
  Las imagenes embebidas suelen tener mas compresion o menos dpi: tolera OCR sucio (guiones rotos, letras pegadas) pero si un campo sigue ilegible -> ninguno, no rellenes por contexto del correo.

CORREO CON MAS DE UNA IMAGEN O MAS DE UN PDF:
  El backend procesa cada binario por separado (una peticion = un solo archivo). Aunque el correo tenga 2, 3 o mas capturas adjuntas o embebidas, tu SOLO ves el de esta peticion.
  REGLA SISTEMA (Excel / auditoria de pagos): **un pago = una imagen (o una pagina PDF relevante) = una fila digitalizada**. No fusiones dos comprobantes en un JSON; no completes campos con datos de otra captura del mismo hilo que no esta en este binario.
  REGLA: 1 imagen (o 1 PDF de una pagina relevante) = como maximo 1 clasificacion y 1 JSON = 1 pago en Excel. No agrupes varias capturas en un solo resultado; no rellenes campos con datos que "imaginas" de otras imagenes del mismo mensaje.
  Cada binario se evalua con las MISMAS reglas de plantilla: A (imagen 1), B (imagen 2), C (imagen 3 / Binance), D (imagen 4 / BDV) o ninguno. Una pieza puede ser A, otra del mismo correo B y otra ninguno: es correcto e independiente.
  Si esta pieza es basura (firma, icono, segunda copia ilegible) -> ninguno; no intentes completar un pago usando otra captura que no esta en pantalla.
  MEZCLA EN UN SOLO BINARIO (collage, captura de bandeja, correo escaneado, PDF de hilo Gmail): Si se ven **varias** miniaturas o trozos de **distintos** documentos y **no** puedes aislar **un solo** comprobante cuyo **fecha_pago**, **monto** y **numero_referencia** pertenezcan sin ambiguedad al **mismo** ticket (sin mezclar cifras de dos depositos) -> **formato "ninguno"** y NA. No inventes una fila "promedio" ni cruces datos entre recortes.
    Excepcion (misma regla para A/B/C/D): Si **un** nucleo de comprobante es **claramente dominante y legible** (ej. recibo BNC con 0191 + RAPI + Serial/Ref + monto + fecha; **pantalla Binance Pay** con USDT/USD + Id de orden + exito; **comprobante BDV** con **0102** + titular empresa + **SECUENCIAL NRO** o secuencial legible + **Total Efectivo/Deposito** + **FECHA/HORA** del mismo bloque) y el resto es chrome de correo (cabeceras Gmail, botones Responder/Reenviar), barra de estado movil, firma, icono o un segundo documento **borroso o parcial sin datos operativos utiles**, clasifica **solo** ese nucleo (BNC -> **B**, Binance -> **C**, BDV -> **D**) y extrae campos **unicamente** de ese bloque; no rellenes huecos con el trozo ilegible.
    Si en la misma pieza hay **dos o mas** comprobantes del mismo tipo (ej. dos recibos BNC; dos pantallas Binance; **dos comprobantes BDV** enteros) y asignar monto/referencia (y fecha si aplica) obligaria a **adivinar** cual corresponde a cual -> **ninguno** (el backend manda **una** peticion por archivo: **un pago = una imagen/pagina = una fila**; no generes dos JSON en una sola respuesta).
  ORIENTACION / ROTACION — Mercantil (A): El mismo comprobante (A1 papel **DEPOSITO DIVISAS** o A2 **tira RECAUDACION** con 0105) puede llegar **fotografiado o escaneado en cualquier angulo** (0°, 90°, 180°, 270°) o levemente inclinado. Clasifica por **texto y diseno** (etiquetas Cédula Dep., Monto, Fondos RECAUDACION, cuenta 0105, RAPI-CREDIT, bloque DCME/YYYYMMDD en codigo guionado, pie **PDP. 056** cuando aparezca), no por si el papel esta "vertical" u "horizontal" respecto a la foto. Si tras mentalmente rotar la imagen el nucleo A (Mercantil) es claro y los campos obligatorios son legibles -> **A**; si sigue ilegible -> **ninguno**.
  Regla anti-falso-negativo Mercantil A1 (fotos reales): si ves formulario **DEPOSITO DIVISAS** + marca **Mercantil** + cuenta **0105** + titular **RAPI-CREDIT** y un bloque operativo impreso (tira/validador) con **Monto USD** y **Serial**,
  clasifica **A** aunque haya sombras, reflejos, imagen oscura, pliegues del papel, manuscritos grandes o parte del borde recortado.
  ORIENTACION / ROTACION — BNC (B / imagen 2): El **recibo de cajero BNC** (papel seguridad, logo **BNC**, cuenta **0191**/..., **Deposito Us$**) puede llegar en **cualquier giro** (horizontal, vertical, 90°/180°/270°, leve inclinacion). Lee el bloque como si rotaras mentalmente la foto hasta alinear lineas **Agencia/Terminal/Cajero**, **Cuenta**, **DP:**, **Serial/Ref** y la linea de **monto** con asteriscos; no rechaces por "el logo quedo de lado". Si con esa lectura el nucleo B (PASO 2) es claro y fecha/monto/ref salen de **ese** mismo ticket -> **B**; si tras rotar sigue ilegible o ambiguo entre dos depositos -> **ninguno**.
  ORIENTACION / ROTACION — Binance Pay (C / imagen 3): La **captura de app** (fondo oscuro tipo Binance, barra de estado, flecha **atras** arriba, circulo **verde** con tilde, bloque **Pago exitoso** / Payment successful, importe **USDT** o USD grande, **ID de orden**) puede llegar **rotada o inclinada** como foto de telefono. Lee mentalmente **0°/90°/180°/270°** hasta que titulos, monto e id queden legibles; no descartes por "el check quedo arriba o abajo". Si tras rotar ves nucleo C (PASO 2b) con **monto** e **identificador de orden** sin ambiguedad -> **C**; si solo queda un trozo con check verde **sin** monto **y sin** ristra larga de orden -> **ninguno** (no inventes USDT ni Order ID desde asunto/cuerpo del correo).
  ORIENTACION / ROTACION — BDV (D / imagen 4 / BNV): El **comprobante Banco de Venezuela** llega como **hoja horizontal ancha** (franja roja izquierda, logo, bloques DATOS DE LA CUENTA / TRANSACCION) o como **tira termica estrecha vertical** (agujeros de archivo, texto en columnas, SECUENCIAL NRO a veces impreso **siguiendo el borde** del papel). Puede estar **fotografiado girado 90°/180°/270°** o inclinado. Lee mentalmente rotando hasta alinear **0102-...**, **TITULAR DE LA CUENTA**, **SECUENCIAL NRO** / numero rojo de operacion, **TOTAL EFECTIVO**/**TOTAL DEPOSITO** y **FECHA**/**HORA**; no confundas **orientacion de la foto** con tipo de banco. Si tras rotar el nucleo D (PASO 2a) es claro y fecha/monto/ref salen del **mismo** comprobante -> **D**; si hay dos depositos BDV completos en un solo binario y mezclarias cifras -> **ninguno**.
  Caso limite BDV (muy tenue): si la impresion esta lavada o de bajo contraste pero todavia se reconoce marca BDV/Banco de Venezuela + estructura de comprobante de transaccion + numero operativo rojo/lateral, conserva D cuando puedas leer con certeza monto y una referencia operativa del mismo documento.

OBLIGATORIO — campo "formato" en el JSON: SOLO uno de estos seis valores exactos: A, B, C, D, NR, ninguno.
  A = plantilla imagen 1: ticket RAPI-CREDIT / RECAUDACION / terminal (abajo) O papeleleta Mercantil DEPOSITO DIVISAS a RAPI-CREDIT con RECAUDACION (VARIANTE MERCANTIL).
  B = unicamente plantilla imagen 2 (recibo BNC a favor de RAPI-CREDIT descrita abajo).
  C = plantilla imagen 3: pantalla Binance / Binance Pay de pago exitoso (PASO 2b). **Logo o marca Binance visible en la imagen = confirmacion de Binance** (imagen 3), ademas del nucleo de pago completado.
  D = plantilla imagen 4: comprobante **Banco de Venezuela (BDV)** —deposito en cuenta / transaccion impresa— con cuenta **0102-...** y titular de cuenta **empresa** en USD (u otra divisa impresa): **RAPI CREDIT** u otra razon social en la misma linea **Titular** (ej. **SOFT CREDIT C.A.**). Ver PASO 2a y FORMATO D. **No es BNC** (Banco Nacional de Credito) ni Mercantil (0105) ni ticket RECAUDACION vertical A.
  NR = comprobante bancario reconocible pero **no** a favor de RapiCredit (ver FORMATO NR); "monto" debe ser el literal **NR**.
  ninguno = cualquier otra cosa, duda, borroso, selfie, documento que no sea esas cinco plantillas anteriores cuando aplique.
Prohibido usar otro valor en "formato" (ni numeros, ni texto libre).

REGLA SISTEMA A/B/D (imagen 1, 2 y 4): Devuelve "A", "B" o "D" solo si el comprobante coincide con esa plantilla y puedes extraer con valor real
fecha_pago, monto y numero_referencia desde la imagen/PDF. El campo cedula en JSON debe ser siempre "NA" (ver REGLA CEDULA).
  Si la plantilla parece A, B o D pero falta fecha, monto o referencia legible, formato "ninguno" y NA.

REGLA SISTEMA C (imagen 3 / Binance Pay): Devuelve "C" si ves el nucleo C (PASO 2b) y con certeza: monto (USDT/USD) y numero_referencia (Id. de orden u otro id largo de la pantalla).
  En el JSON pon siempre fecha_pago="NA", cedula="NA" y email_cliente="NA" (el backend usa el remitente del correo para cliente y cedula).
  Si falta monto o id de orden con certeza -> "ninguno".

COLUMNAS OBLIGATORIAS Y GMAIL (etiquetas de usuario — las aplica el backend; no gestiona estrellas):
  A, B y D: fecha_pago, monto y numero_referencia reales desde la imagen; cedula siempre "NA" en JSON.
  C: monto y numero_referencia desde la imagen; fecha_pago, cedula y email_cliente "NA" en JSON.
  El pipeline evalua cada imagen/PDF por separado: varias piezas validas en un correo generan varias filas. La cedula en Excel la resuelve el backend con tabla clientes por email De.

=== CLASIFICACION EN ORDEN (sigue el orden; no inviertas B y A) ===
Objetivo: decidir formato en pocas comprobaciones. Cada peticion es UNA sola pieza: clasifica solo lo visible ahi; mismas reglas imagen 1 (A), imagen 2 (B), imagen 3 (C) e imagen 4 (D). No cruces datos entre capturas.

PASO 1 - DESCARTE (ninguno al instante):
  No aparece RAPI-CREDIT (ni RAPI CREDIT / RAPICREDIT / RAPH-CREDIT / RAPICREDI razonable) y tampoco BNC reconocible
    y tampoco es la variante Mercantil DEPOSITO DIVISAS descrita en "VARIANTE A — MERCANTIL" abajo
    y tampoco es comprobante Banco de Venezuela BDV con nucleo D (PASO 2a: **0102** + titular empresa tipo **...CREDIT...** u otra razon en cuenta, ej. RAPI CREDIT / SOFT CREDIT)
    y tampoco es pantalla Binance Pay imagen 3 (PASO 2b)
    y tampoco aplica **FORMATO NR** (comprobante bancario claro a otro beneficiario distinto de RapiCredit) -> ninguno.
  Es captura de app generica, Pago Movil no Binance Pay, Zelle, otro banco distinto (salvo Mercantil con RAPI+RECAUDACION), selfie, publicidad, borroso sin datos -> ninguno.
  Excepcion: NO descartes como "solo app" si cumple nucleo C (PASO 2b): Binance/Binance Pay + pago exitoso + USDT o USD + identificador de orden; el email en pantalla no es obligatorio si hay CONTEXTO_REMITE en el mensaje del sistema.
  Regla de atajo temprano A1 (Mercantil): si detectas **DEPOSITO DIVISAS** + marca **Mercantil** + cuenta **0105** y un **bloque termico lateral izquierdo**
    con lineas tipo **Cedula Dep. / Serial / Monto / Fondos / RAPI-CREDIT**, NO descartes por manuscritos, giro o fondo oscuro; enruta directamente a evaluacion de formato **A**.

PASO 2 - Prioridad B (imagen 2) si el nucleo B se cumple; entonces B, no A ni C:
  Nucleo B = (BNC logo o texto) + cuenta con barras ####/####/##/######## (ej. 0191/0127/...) + RAPI-CREDIT como titular o beneficiario de esa cuenta
    + monto en dolares visible (Us$, US$, USD, o patron *...*NN.mm con decimales).
  Regla anti-falso-negativo BNC (fotos reales): si el papel muestra patron de seguridad BNC (fondo repetido con emblema), texto BancoNacionaldeCrédito/BNC,
    cuenta 0191/... de RAPI-CREDIT y linea Deposito Us$ con monto enmascarado por asteriscos, clasifica B aunque el contraste sea bajo,
    haya sombra, desenfoque leve, sello azul, reflejo o parte del borde recortado.
  Si el nucleo B se cumple, elige B aunque tambien aparezca "RAPI-CREDIT" en otro contexto: aqui es recibo de cajero BNC, no ticket RECAUDACION.
  VARIANTE B — **patrones visuales tipicos del recibo BNC (imagen 2)** (combinar varias senales; no inventes si falta el nucleo):
    - **Marca BNC**: texto **BNC** destacado y/o icono sol/abanico; a veces **Rif. N° J...** en margen; agua/fondo repetitivo tipo seguridad.
    - **Cuenta destino** en linea **Cuenta** con formato **0191/0127/48/2300080639** (cuatro grupos con barras; prefijo **0191** es senal fuerte frente a **0105** Mercantil y **0102** BDV).
    - **Beneficiario** de esa cuenta: **RAPI-CREDIT, C.A** / **RAPI-CREDIT** (OCR: BAPI-, RAPH-); confirma que el deposito es **a favor de RapiCredit** (si el beneficiario impreso es otro y no es nucleo NR -> no fuerces B).
    - **Deposito en divisas**: lineas **Deposito Us$**, **Deposito U.S$**, **Debito**/**Us$** en contexto de cajero; el importe suele ir como **asteriscos +** cifra con punto decimal (ej. **********142.00) — senal fuerte **B** frente a muchos tickets A.
    - **Metadatos de ventanilla**: **Agencia:** nombre sucursal; **Terminal:**; **Cajero:** (usuario); **fecha y hora** tipo DD/MM/YYYY HH:MM:SS; **Serial:** y **Ref:** (dos numeros, a veces cercanos pero distintos) — para **numero_referencia** sigue el discriminador "IMAGEN 2 / B" mas abajo.
    - **Depositante en papel**: linea **DP:V-** / **DP:E-** / **DP:J-** + digitos + nombre (misma linea o continua); **solo** para decidir A vs B: si hay **recibo BNC** + **0191** + agua/sello BNC -> **B**, no A, aunque el patron DP recuerde al ticket Mercantil.
    - **Caso comun en fotos de telefono**: el valor de **Ref** puede verse dos veces (una impresion tenue y otra mas oscura/manuscrita encima). Para `numero_referencia`,
      prioriza la cadena de digitos mas legible asociada a la etiqueta **Ref**; si hay conflicto visual, usa la que tenga mejor nitidez y longitud coherente (usualmente 7-9 digitos).
    - **Serial visible sin Ref limpio**: si **Ref** esta borroso o parcialmente tapado pero **Serial** es legible en el mismo bloque de operacion BNC, acepta B y usa `Serial` como `numero_referencia`
      (sin usar cuenta 0191/... ni monto como referencia).
    - **BNC monocromo / bajo contraste**: no exijas tinta azul intensa ni logotipo perfecto; acepta OCR sucio de "BancoNacionaldeCredito", "Deposi to Us$", "Serial", "Agencia", "Terminal", "Cajero"
      mientras el patron estructural BNC sea consistente.
    - **Sello azul** "Banco Nacional de Credito/Crédito", **RECIBIDO**, agencia, "Deposito Us$", cajero — refuerza **B**; no es comprobante BDV (D) ni Mercantil (0105).
    - **Correo digitalizado / captura con varias imagenes**: el backend puede enviar **esta** pieza sola (adjunto o recorte). Si aqui ves un recibo BNC **completo** aunque el borde muestre parte de otra foto o UI, aplica VARIANTE B y la regla de MEZCLA arriba: extrae **solo** del ticket BNC; no supongas datos de otra miniatura que no se vea en este binario.
  Refuerzos utiles de B (opcionales si el nucleo ya es claro): asteriscos antes del monto; Agencia / Terminal / Cajero; **Ref.** / **Ref:** / **Rif. N°** arriba o al costado; **Serial:** con cadena de digitos (a menudo **8-9 cifras**, no confundir con cuenta 0191/...); layout en **dos columnas** (izquierda agencia/cuenta/DP; derecha fecha/hora/serial/ref).
  Depositante: linea **DP:V-...** nombre (clasificacion) **o** linea **RIF: J-...** nombre si es deposito empresa/persona juridica — ambas en recibo BNC; OCR puede leer **BAPI-CREDIT** por error donde dice **RAPI-CREDIT**: si el resto es nucleo B (0191, BNC, beneficiario coherente), sigue siendo **B**.
  **Sello azul** de ventanilla (ej. "RECIBIDO CAJERO", agencia, "Deposito U.S$" / "Deposito $") **no** cambia el formato: sigue siendo **imagen 2 (B)** si hay logo BNC + cuenta 0191/... + RAPI; **no** es imagen 4 (D): D es **Banco de Venezuela + 0102**, no BNC.
  REGLA FIJA — linea DP + recibo BNC: Si el papel es claramente **recibo de cajero BNC** (sello o texto legible "Banco Nacional de Credito" / "Banco Nacional de Crédito" / marca BNC,
    fondo con lineas azules o patron de matriz de cajero, cuenta ####/####/##/######## con RAPI como titular, tipico comprobante horizontal BNC)
    **y** en la misma pieza aparece la linea del depositante **DP:** seguida de **V-** o **E-** o **J-** y digitos de cedula **con el nombre en la misma linea**
    (ej. `DP: V-015185092` y a continuacion `MIRAIDA JIMENEZ`, con o sin guion entre cedula y nombre) -> **formato B (imagen 2) SIEMPRE**, **nunca A (imagen 1)**,
    aunque el OCR tambien capte "RAPI" o "RAPI CREDIT" (en BNC es titular de cuenta, no ticket RECAUDACION vertical). Esta regla prevalece sobre "DP:...-NOMBRE refuerza A".
  REGLA FIJA — **Banco Mercantil = imagen 1 (A)**, no B: Si la cuenta cliente o el comprobante muestra codigo **0105** al inicio del numero de cuenta
    (formato `0105-0120-22-5120135978`, `0105 0120 22 5120135978`, `0105 0121 21 ...` u OCR sucio parecido), eso es **Banco Mercantil** en Venezuela -> **formato A** (variante Mercantil o ticket RECAUDACION), **nunca B (BNC)**.
    Aplica a: (1) **tira termica/validador** vertical u orientada (SPD/DCME/HOME, Cedula Dep., Fondo RECAUDACION, RAPI-CREDIT o OCR "RAPH-CREDIT"); (2) **formulario papel "DEPOSITO DIVISAS" / "DEPÓSITO DIVISAS"** con logo **Mercantil** y tira impresa con Refer/Serial/Monto USD/RECAUDACION.
    El recibo BNC tipico usa cuenta destino con otro codigo de entidad en el patron cajero (ej. **0191**/... con slashes), no confundir con 0105 Mercantil.

PASO 2a - D (imagen 4 / Banco de Venezuela BDV) si PASO 2 NO aplico (no es recibo BNC) y el papel es BDV:
  Nucleo D = institucion **Banco de Venezuela** (texto "Banco de Venezuela", siglas **BDV**, logo triangulos/amarillo-azul-rojo, franja vertical **"TARJETAS"** / **DEPOSITOS** / **DEPÓSITOS** / **PAGOS** / mezcla **DEPOSITOS / PAGOS / TARJETAS** a menudo en **barra roja o color** al margen izquierdo) **y NO** es BNC (no "Banco Nacional de Credito" / marca BNC de cajero ####/####/##/######## como en imagen 2).
    + Titular / beneficiario de la cuenta en USD (u otra linea clara en **TITULAR DE LA CUENTA** / datos cuenta): **RAPI CREDIT** o **SOFT CREDIT C.A.** u otra razon social **empresa** coherente con cuenta corporativa (no exijas la palabra "RAPI" si el resto es claramente BDV + 0102 + titular impreso).
    + Comprobante de **deposito en cuenta** o **Comprobante de Transaccion** / **Deposito en Cuenta** / **Pago** con monto en **USD** (o divisa impresa coherente).
    + Cuenta con formato tipo **0102-....** u OCR sucio (0102 es entidad BDV; no confundir con 0105 Mercantil ni 0191 BNC).
  Si el nucleo D se cumple -> **formato D**, no B (aunque sea deposito) ni A (no es ticket RECAUDACION vertical ni Mercantil 0105).
  Regla anti-falso-negativo BDV/BNV (fotos reales): si el comprobante horizontal o vertical muestra marca BDV/Banco de Venezuela,
    cuenta 0102-..., titular corporativo (ej. RAPI CREDIT C.A.) y bloque transaccional con monto/referencia/fecha parcialmente legibles,
    clasifica D aunque haya sello azul atravesado, manuscritos encima, contraste bajo, reflejo o OCR incompleto en lineas secundarias.
  REGLA OBLIGATORIA — **depositante vacio NO invalida D**: Muchos comprobantes BDV traen **DATOS DEL DEPOSITANTE** / **Nombre del depositante** / **CI o RIF del depositante** **en blanco** (sin imprimir ni manuscrito). Eso es **normal**. Si hay BDV + **0102** + titular cuenta + **Total Efectivo** o **Total Deposito** o **Monto Total** + **fecha** y **hora** + un **secuencial** o numero de operacion legible -> **formato D** con JSON completo (fecha_pago, monto, numero_referencia). **Prohibido** devolver **ninguno** solo porque falte cedula o nombre del depositante en el papel.
  numero_referencia: preferir linea **SECUENCIAL NRO** / **Secuencial Nro** (a menudo **13 digitos con ceros a la izquierda**, ej. 0000091316488, 0000000356323). Si **no** ves la etiqueta literal pero en la cabecera hay **dos** numeros de operacion (uno **largo con ceros** y otro en **rojo** mas corto), usa el **largo completo** como numero_referencia; si solo uno es legible, usa ese. Si ademas hay el **mismo** numero en **rojo** sin ceros o mas corto, prioriza la cadena **completa** con ceros que corresponda al secuencial; no uses solo el monto ni la cuenta 0102.
  fecha_pago: fecha y hora impresas en el comprobante (DD-MM-YYYY o formato legible).
  REGLA FIJA — **BNC (imagen 2) gana sobre D**: si el documento es claramente recibo **Banco Nacional de Credito** con patron BNC + cuenta ####/####/##/######## -> **B**, nunca D.
  REGLA FIJA — **Mercantil (0105) gana sobre D**: cuenta que empieza en **0105** + RAPI + RECAUDACION -> **A**, nunca D.

  VARIANTE D — **patrones visuales tipicos BDV (imagen 4 / BNV)** (combinar senales; no inventes campos que no esten en el papel):
    - **Barra vertical roja** (u otro color fuerte) en margen izquierdo con texto **DEPOSITOS / DEPÓSITOS / PAGOS / TARJETAS** (a menudo mezclados con slash) en **blanco** — patron muy frecuente en hoja ancha; en tira vertical puede aparecer como franja o titulos laterales.
    - **Marca BDV**: triangulos amarillo-azul-rojo y texto **Banco de Venezuela** / **BDV**; titulo **COMPROBANTE DE TRANSACCION** / **DEPOSITO EN CUENTA** / **PAGO** (tildes OCR opcionales).
    - Cuenta tipo **0102-....** (grupos con guiones; prefijo **0102** discrimina de **0105** Mercantil y **0191** BNC). Ejemplo frecuente en operaciones Rapi: `0102-0391-190002058270` (solo ejemplo; copia el numero **tal como** se vea en la imagen).
    - **Titular**: **RAPI CREDIT C.A** / **RAPI CREDIT** / **SOFT CREDIT C.A.** en linea **TITULAR DE LA CUENTA** (espacios OCR variables).
    - **Secuencial**: bloque **SECUENCIAL NRO** / **Secuencial Nro** con cadena larga (muchos **ceros a la izquierda**); a veces **duplicado** con numero en **tinta roja** mas corto en cabecera — sigue reglas de **numero_referencia** ya definidas arriba (prioriza secuencial completo etiquetado).
    - **Monto**: lineas **TOTAL EFECTIVO**, **TOTAL DEPOSITO**, **MONTO TOTAL**; decimales con **coma** venezolana (ej. 100,00) o punto segun impresion; puede haber **monto en letras** (CIEN CON 00/100) y **anotacion manuscrita** ("110 $") — **prioriza cifra impresa del comprobante** del bloque TOTAL; no inventes monto desde notas al margen si la cifra impresa es ilegible.
    - **Sello de oficina** (rectangulo azul/morado, oficina, **CAJA N°**, fecha de sello): refuerza D; **no** sustituye **0102** + titular + secuencial + total. Si la **fecha del sello** difiere de la linea impresa **FECHA:** junto al secuencial y ambas son legibles, usa para **fecha_pago** la pareja **FECHA** + **HORA** del **bloque de transaccion impreso** (cabecera cerca de SECUENCIAL NRO), no mezcles dia de sello con hora del cuerpo salvo que una de las dos sea ilegible y la otra complete inequivocamente la misma operacion.
    - **Sello cruzado sobre el comprobante** (como "Banco de Venezuela ..."): si tapa parte del centro, sigue siendo D cuando el resto conserva
      cuenta 0102, titular y al menos una referencia operativa legible (secuencial o numero de operacion). No bajes a ninguno solo por superposicion del sello.
    - **Manuscrito encima del bloque central** (nombre/telefono/nota): ignora manuscritos para clasificar banco; usa primero datos impresos.
      Solo toma manuscrito para completar fecha o referencia si el trazo coincide claramente con una etiqueta del comprobante y no contradice lo impreso.
    - **Cabecera tenue o recortada**: acepta OCR parcial de "COMPROBANTE DE TRANSACCION"/"DEPOSITO EN CUENTA" si se mantiene el nucleo BDV
      (marca BDV + 0102 + titular empresa + monto/referencia en mismo bloque).
    - **Manuscritos** (placa, "2da cuota", moto, nombres al pie): **no** uses para **cedula** en JSON (REGLA CEDULA); no uses **marca de tiempo de camara** en borde de foto como fecha_pago.
    - **Depositante en blanco**: normal; **no** invalida D si hay monto + secuencial + fecha/hora + 0102 + titular.
    - **Correo escaneado / Gmail / varias imagenes**: si la pieza incluye marco de cliente de correo pero el **comprobante BDV** ocupa el area dominante con datos legibles, clasifica **D** y extrae **solo** del papel BDV (misma logica MEZCLA — excepcion dominante).

  VARIANTE D1 — **Tira vertical / termica BDV (imagen 4 tipica)** — mismo formato D:
    Puede ser **tira estrecha vertical** (impresion matriz de puntos o termica), agujeros de archivo arriba, foto inclinada; texto en columnas verticales.
    Titulos frecuentes: **"Comprobante de Transaccion"**, **"Deposito en Cuenta"**, **"Pago"** (o OCR sucio: Transaccion sin tilde).
    Secciones con lineas punteadas: **DATOS DE LA CUENTA**, **DATOS DE LA TRANSACCION**, **DATOS DEL DEPOSITANTE** (a veces **en blanco**), **DATOS DEL CAJERO** (**Usuario**, **Oficina Deposito**); pie **PAG. 1/1** opcional.
    **Titular de la cuenta**: RAPI CREDIT C.A. / RAPI CREDIT / SOFT CREDIT C.A. (no exige "RECAUDACION" como imagen 1 Mercantil).
    **Nro. cuenta** tipo `0102-0391-190002058270` (0102 + grupos); moneda **USD**, cuenta **Corriente** u similar.
    **Secuencial Nro** / secuencia larga (ej. `0000000356323`): usar como **numero_referencia** prioritario si identifica la operacion.
    **Monto Total** / **Total Efectivo** / **Total Deposito** / monto en cifras y a veces **en letras** (ej. "CIEN CON 00/100"); puede haber **monto manuscrito** "$" en el centro — prioriza cifra impresa del sistema si hay ambas.
    **Sello azul** rectangular con logo BDV y texto de **oficina** (ej. "431-ALTAGRACIA", "401 - OFICINA UPATA", codigo + nombre sucursal); refuerza D pero no sustituye **0102** + titular + secuencial.
    Campos utiles OCR: **Oficina Deposito**, **Usuario** (cajero, ej. NM36837), **Fecha** y **Hora** en una o dos lineas.
    Manuscrito al pie (nombre, CI, "R.F-..."): **no** uses para JSON de cedula (REGLA CEDULA); solo refuerzo visual de deposito en ventanilla.
    No es imagen 1 (A): aunque la tira sea vertical, si dice **Banco de Venezuela** + **0102** + titular empresa en cuenta -> **D**, no Mercantil ni RECAUDACION SPD.

  VARIANTE D2 — **Comprobante horizontal / hoja ancha BDV (imagen 4)** — mismo formato D:
    Logo **Banco de Venezuela** arriba a la izquierda; titulo centrado **COMPROBANTE DE TRANSACCION** / **DEPOSITO EN CUENTA** / **PAGO**; fuente matriz de puntos.
    **Franja vertical roja** (u otro color fuerte) en margen izquierdo con texto **DEPOSITOS / PAGOS / TARJETAS** (con o sin tilde en Deposito) — patron **muy frecuente** en hoja ancha BDV; refuerza D junto con **0102**.
    **SECUENCIAL NRO** suele ir arriba a la derecha; a veces **duplicado**: numero largo con ceros **y** numero en **tinta roja** mas corto (mismo operativo) — preferir el valor bajo etiqueta **SECUENCIAL NRO** con todos los digitos visibles.
    En esta variante horizontal pueden aparecer: (a) manuscrito grande en el centro, (b) sello rectangular oblicuo encima de fecha/caja, (c) foto con perspectiva.
    Si aun existe trazabilidad clara del bloque transaccional impreso, clasifica D y extrae desde el texto impreso visible.
    Variante frecuente adicional: comprobante girado con **numero rojo vertical en borde derecho** y texto central tenue; ese patron sigue siendo D si coincide con marca BDV y layout de transaccion.
    **Total Efectivo** / **Total Deposito** / **Monto Total** en bloque inferior; pie **Original: Cliente** en rojo en algunos ejemplos; codigo de forma **CN. 030** u similar en pie — refuerzo BDV, no obligatorio.
    Sello azul cuadrado/rectangular (caja, oficina, CAJA N°); puede haber firma boligrafo sobre el sello — sigue siendo D.
    Misma regla **0102** + BDV + titular + secuencial + monto; **depositante en blanco** OK; no confundir con BNC (0191) ni Mercantil (0105).

PASO 2b - C (imagen 3 / Binance Pay) si PASO 2 y 2a no aplicaron (no es recibo BNC ni comprobante BDV imagen 4):
  Nucleo C = evidencia de app o web Binance / Binance Pay **y** datos minimos **en esta pieza**: **monto** (USDT o USD del pago) **y** **numero_referencia** (Id. de orden u otro id largo de la pantalla). Sin ambos -> **ninguno** (no completes con asunto del correo, cuerpo del mensaje ni nombre de archivo).
  **Logo o marca Binance visible = indicio confirmado** de que la plataforma es Binance (formato C), no otra wallet:
    - Isotipo rombo/diamante amarillo-dorado, logo amarillo sobre fondo oscuro, texto **Binance** o **Binance Pay** en cabecera o pie, iconografia oficial de la app.
    - Si ves ese logo/marca con claridad **y** ademas monto + id en la misma captura, trata la pieza como Binance Pay; no la clasifiques A ni B.
    - Un circulo verde con check **solo** (cabecera de exito recortada), **sin** importe **USDT**/USD visible **y sin** bloque numerico largo (>=10 digitos) de orden en **esta** imagen, **no** basta: puede ser otra app o solo la parte superior de la pantalla -> **ninguno** hasta que en el binario se vean monto + ref (o regla de recorte amplia abajo).
    + Ademas: layout tipico de la app, colores de marca, o texto "Binance" en cualquier zona legible.
    + pantalla de transaccion completada o exitosa (no login, no listado vacio). Titulos equivalentes (uno basta; tolera OCR sucio):
      "Pago completado", "Payment completed", "Pago exitoso", "Pago realizado", "Payment successful", "Completed", "Successful", "Enviado" (solo si es claro que es confirmacion de pago).
    + indicio de exito: circulo o boton verde con check (a veces check **blanco** dentro del circulo verde, a veces check **negro** segun tema), tilde de confirmacion, banner de exito; tema **oscuro** (gris/negro/azul muy oscuro) muy frecuente en capturas Binance.
    + importe principal en USDT o USD legible (ej. "160 USDT", "95 USDT", "122 USDT", "50.5 USDT"). Prioriza **USDT** en grande como senal fuerte de app crypto (Binance Pay), distinta de comprobante bancario USD en papel o tira.
    + identificador: etiqueta **Id. de la orden**, **Order ID**, **ID de orden**, **Order No.** o bloque de **10-22** digitos contiguos en la pantalla de confirmacion (Binance suele 15-19 digitos; si la captura corta el final, copia los digitos visibles consecutivos que veas).
  VARIANTE C — **patrones visuales tipicos Binance Pay (imagen 3)** (combinar senales; no inventes):
    - **Chrome movil**: barra superior (hora, bateria, wifi); flecha **atras** arriba a la izquierda; botones inferiores tipo **Listo**, **Enviar otro** — refuerzan app, no sustituyen monto/id.
    - **Bloque central**: circulo verde grande + texto **Pago exitoso** / equivalente; debajo cifra **NN USDT** (o USD) en tipografia grande.
    - **Destinatario**: linea **A** / **To** con alias (ej. **Rapicredit**) y a veces correo **operaciones@rapicreditca.com** u otro de empresa; ese correo en pantalla es del **beneficiario**: para JSON **email_cliente** sigue la regla abajo (NA si solo corporativo).
    - **Metodo / detalle**: "Cuenta Spot y de Fondos", "Ver detalles", "Metodo de pago" — refuerzo C, no obligatorio para clasificar si ya hay logo Binance + monto + id.
    - **Correo Gmail / bandeja digitalizada**: si la pieza incluye **marco de Gmail** (cabecera De/Asunto, botones Responder/Reenviar/Compartir) y debajo o al costado sigue viendose **la captura Binance** con monto + Id de orden, ignora el marco del correo para **clasificar C** y extrae **solo** de la zona de la app (no uses fecha del asunto como fecha_pago: en C va **NA**).
    - **Combinacion de imagenes en un correo**: el backend procesa **esta** pieza sola; otra adjunta no esta en pantalla. Si aqui solo ves **una** confirmacion Binance completa aunque el borde recorte botones o banner promo, aplica MEZCLA (excepcion dominante) y VARIANTE C.
  Si la captura esta recortada: basta senal clara de app (barra de estado movil, flecha atras, tema oscuro/claro tipo wallet) + monto **USDT** o USD + check/exitoso + **cualquier** ristra numerica larga visible (>=10 digitos) como numero_referencia; no devuelvas "ninguno" solo porque falte la etiqueta literal "Order ID".
    - numero_referencia: copia el Id. completo; si hay varios numeros largos, el que acompane a "orden" / "Order" / "ID"; si no hay etiqueta, el bloque de **10+** digitos mas largo o mas centrado en la zona de detalle del pago (no numeros de hora/fecha sueltos de 6-8 digitos si hay otro bloque mas largo).
    - email_cliente: debe ser el correo del PAGADOR (cliente persona) si aparece en pantalla. Si solo ves correo corporativo del BENEFICIARIO (ej. operaciones@..., pagos@..., cuenta de la empresa receptora), NO lo uses como email_cliente: pon "NA" o usa CONTEXTO_REMITE (From del correo), que es quien envia el comprobante.
  NO es C: otra exchange (Bybit, OKX, ...) con marca clara distinta, solo historial sin confirmacion, transferencia bancaria tradicional en PDF de banco, captura **sin** monto **y sin** ningun bloque numerico largo de orden.
  Si nucleo C: formato C (no A, B ni D). Extraccion: monto, numero_referencia; fecha_pago=NA; cedula=NA; email_cliente NA en JSON (backend usa remitente).

REGLA ANTI-CONFUSION — imagen 3 (C / Binance Pay) vs imagen 1 (A / Mercantil tira):
  Muchos falsos negativos: pantalla movil "Payment Successful" / "Pago exitoso" + **USDT** + check verde se clasifican mal como A por ristras numericas que recuerdan serial Mercantil (7400...).
  **Nunca** elijas formato A si la pieza es claramente **pantalla de app** (barra superior hora/bateria, flecha atras, tipografia app) con **USDT** y mensaje de pago exitoso, **aunque** aparezcan digitos largos: eso es **C**, no comprobante Mercantil.
  Formato A requiere **papel o tira termica de banco**: texto RAPI-CREDIT + RECAUDACION en contexto de deposito, o papeleta DEPOSITO DIVISAS, o ticket vertical monoespaciado; no basta un numero largo sin ese contexto bancario.
  Si ves USDT + exito en app y **no** ves RAPI+RECAUDACION en tira/papel legible -> **PASO 2b gana: C**.
  Si ves **logo/marca Binance** + pantalla de **pago exitoso** con **monto USDT/USD** e **Id de orden** (o regla de captura recortada con >=10 digitos) en **esta** pieza -> **C** (imagen 3); no fuerces A por digitos tipo serial bancario. **Logo Binance sin monto o sin id largo visible** -> no es C completo; **ninguno** si faltan datos obligatorios (REGLA SISTEMA C).

PASO 3 - A (imagen 1) solo si PASO 2, 2a y 2b no aplicaron:
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

PASO 5 - Extraccion: A, B o D si fecha_pago, monto y numero_referencia son legibles (cedula en JSON siempre NA); C si monto + numero_referencia son legibles con fecha_pago, cedula y email_cliente en NA; si falta monto o referencia -> ninguno y NA.
  En **D (BDV)**, la ausencia de datos del **depositante** en el papel **no** cuenta como "falta de dato" para fecha/monto/ref.

DISCRIMINADOR SERIAL — imagen 1 (A) vs imagen 2 (B) (aplica ademas de RAPI-CREDIT/BNC):
  IMAGEN 1 / A — serial de operacion compuesto por BLOQUES separados por guiones (-) u ocasionalmente /:
    El SEGUNDO bloque (contando de izquierda a derecha o de arriba a abajo en texto vertical) debe ser
    una FECHA como 8 digitos YYYYMMDD (ej. 20260401 = 1 abr 2026). Ejemplo de patron: 9813-20260401-144545-DCME-7643-A.
    Puede incluir DCME, SPDP, letras sueltas al final. Esto NO es una sola ristra de 13+ digitos.
  VARIANTE MERCANTIL (sigue siendo A / imagen 1): en papeleleta "DEPOSITO DIVISAS" / "DEPÓSITO DIVISAS" (Mercantil) a favor de RAPI-CREDIT con Fondos RECAUDACION,
    suele aparecer ADEMAS una linea impresa "Serial:" (o similar OCR: Serlal, Serial) con una cadena de SOLO digitos, a menudo 13+ cifras empezando por 7 (ej. 740087418878065).
    Esa ristra larga en contexto Mercantil+RAPI+RECAUDACION+USD NO es plantilla B: es el numero de operacion del deposito en divisas. Usala como numero_referencia (valor completo, solo digitos) cuando sea el identificador principal visible junto al serial del deposito.
    Si coexisten (1) cadena con guiones y 2do bloque YYYYMMDD tipo 9213-20260331-143046-DCME-0154-A y (2) Serial: 7400... largo, prefiere el Serial largo (digitos) como numero_referencia para esta variante Mercantil, salvo que solo uno sea legible.
  IMAGEN 2 / B — identificadores en **recibo BNC** (no Mercantil):
    Lo habitual es **Serial:** u otra etiqueta seguida de **solo digitos** (frecuentemente **8-9 cifras**, ej. 141810434, 150927684) o **Ref:** / **Ref.** con numero de control (a veces **cercano** al Serial pero distinto en las ultimas cifras).
    Prioridad para **numero_referencia**: (1) valor junto a **Ref:** / **Ref.** / **Referencia** si esta claro como control de operacion; (2) si no, **Serial:**; (3) variantes **Ref: NF 000001327** o con prefijos — copia la cadena **completa** legible (incl. NF y ceros si aporta unicidad).
    Alguna pieza BNC trae **ademas** ristra muy larga solo digitos que empieza en **7** (>12 cifras) en margen; si es el unico id largo y va con BNC+0191+RAPI, usala como numero_referencia; si coexisten Ref corto y ristra 7400... larga, prefiere **Ref** o **Serial** etiquetados en el cuerpo del recibo cuando identifiquen la operacion.
  Si el comprobante cumple criterios de A (terminal) y la linea serial sigue el patron guiones+fecha en 2do bloque -> A.
  Si cumple BNC (no Mercantil DEPOSITO DIVISAS) con Serial/Ref tipico de cajero -> **B**; no exijas ristra >12 digitos para clasificar B.

DISCRIMINADOR CEDULA / MONTO — imagen 1 (A) vs imagen 2 (B):
  IMAGEN 1 / A (ticket recaudacion RAPI-CREDIT **vertical**): En la linea del depositante la CEDULA va JUNTO AL NOMBRE en la MISMA linea,
    casi siempre separados por un guion: ej. DP:V-015185092-MIRAIDA JIMENEZ o DP: V-... seguido de guion y nombre en mayusculas.
    Ese patron refuerza **A solo** en ticket de **terminal/recaudacion** (monoespaciado vertical, RECAUDACION, serial con YYYYMMDD en 2do bloque).
    Si el mismo patron DP: V-... + nombre aparece en **recibo BNC horizontal** con sello/agua Banco Nacional de Credito -> es **B (imagen 2)**, ver REGLA FIJA PASO 2.
  No confundir con solo etiqueta "Cedula Dep" sin nombre en la misma linea.
  VARIANTE MERCANTIL (A) — patrones visibles **solo para clasificar** A vs B (JSON cedula siempre "NA"): la cedula puede estar en varias zonas: (1) impreso "Cedula Dep." / "Cédula Dep" con solo digitos (ej. 0028424570);
    (2) manuscrito en casillas "Nro. de Cédula" con puntos miles (ej. 28.424.570);
    (3) nombre del depositante puede ir manuscrito en "Depositante" e impreso en mayusculas abreviada en la tira del cajero — refuerza que es comprobante Mercantil papel, no BNC.
  En Mercantil DEPOSITO DIVISAS el monto en USD puede ir con asteriscos en la tira impresa (ej. ***********96,00 USD) usando COMA como decimal venezolano; extrae 96.00 USD. Puede coexistir monto manuscrito "96" en casilla — prioriza la linea impresa del sistema si es legible.
  IMAGEN 2 / B (recibo BNC): El MONTO en dolares del deposito casi SIEMPRE aparece con ASTERISCOS (*) inmediatamente antes
    del valor numerico con decimales, ej. **********122.00 o *****96.00 (cantidad de asteriscos variable). Es señal fuerte de plantilla B.
    En A el importe puede mostrarse con USD sin esa cortina de asteriscos tipica de cajero BNC; si ves BNC + linea Debito/Us$ + asteriscos+monto -> B.

FORMATO A — palabras clave y grupos (ticket vertical / terminal: deben cumplirse TODOS los grupos 1-5 de esta lista):
  Grupo 1 (empresa): RAPI-CREDIT | RAPI CREDIT | RAPI-CREDIT, C.A. | RAPICREDIT | RAPICREDI | RAPH-CREDIT (OCR sucio: H por I, falta guion)
  Grupo 2 (concepto): RECAUDACION | RECAUDACIÓN (tolerar sin tilde: RECAUDACION)
  Grupo 3 (moneda): USD en linea de monto o junto al importe
  Grupo 4 (depositante): CEDULA DEP | Cédula Dep | DP:V-... y en la MISMA linea el NOMBRE del depositante tras guion (patron fuerte imagen 1)
  Grupo 5 (operacion): linea de monto con USD (sin exigir asteriscos como en B) y serial con bloques separados por guiones;
    numero_referencia conserva guiones y 2do bloque YYYYMMDD cuando sea visible.
  EXCEPCION IMPORTANTE — papeleta **VARIANTE MERCANTIL (A1) DEPOSITO DIVISAS** (formulario papel + tira validador): NO exijas Grupo 4 de ticket (DP+nombre misma linea).
    Para A1 aplican solo los "Grupos equivalentes" definidos en VARIANTE A — MERCANTIL abajo (cedula en casilla manuscrita o Cédula Dep en tira cuenta; nombre en casilla Depositante aunque este en otra linea).
Palabras secundarias A (refuerzo, no bastan solas): FONDOS, CANT BILLETES, COMISION, TASA, CTA. COM,
  DCME, SPDP, COPIA (vertical), lineas alfanumericas tipo XXXX-YYYYMMDD-hhmmss-...

VARIANTE A — MERCANTIL (dos caras tipicas; ambas son formato A / imagen 1, banco Mercantil):
  (A1) **Formulario papel DEPOSITO DIVISAS**: logo o nombre **Mercantil**; titulo "DEPOSITO DIVISAS" o "DEPÓSITO DIVISAS" (a menudo en **franja o texto vertical** en el margen izquierdo del formulario); formulario **horizontal** con cabecera azul/blanca y casillas para **Código Cuenta Cliente** (0105...), **Fecha**, **Monto**, **Titular de la cuenta** (Rapi-Credit C.A.), **Depositante**, **Nro. de Cédula del Depositante** (manuscrito), **Causa o motivo del depósito**, **Origen de los fondos**, firma.
    Pista explicita de layout (prioridad alta): **foto horizontal de formulario Mercantil con tira vertical a la izquierda** (bloque termico gris con lineas Cedula Dep./Serial/Monto/Fondos y pie tipo PDP.056). Este layout coincide con A1 aunque la foto llegue girada o con perspectiva.
    Tira o sello del validador **superpuesto a la izquierda** (termico o gris): linea superior puede ser codigo **alfanumerico con guiones** (ej. `9238-20260408-083811-DCME-5421-A`: 2do bloque fecha YYYYMMDD); **Cta. / cuenta** 0105-....; **Serial:** ristra larga solo digitos (7400...); **Monto** `***********NN,00` USD; **Fondos: RECAUDACIÓN**; beneficiario **RAPI-CREDIT**; etiquetas tipo **Cédula Dep.**, nombre depositante abreviado. Pie de formulario frecuente **PDP. 056** u OCR sucio del mismo codigo — refuerza A1, no obligatorio.
    Verificacion **sin inventar** (A1 / papel + tira): en **esta** imagen deben leerse **Mercantil** (logo o nombre) + **DEPOSITO DIVISAS** + cuenta **0105** + **RAPI-CREDIT** como titular + **USD**. La palabra **RECAUDACION** en tira/sello es un refuerzo fuerte, pero en fotos movidas/rotadas puede estar parcialmente tapada o borrosa: si el resto del nucleo A1 es claro y puedes extraer **fecha_pago**, **monto** y **numero_referencia** de forma consistente, mantiene **A** (no fuerces "ninguno" solo por OCR incompleto de RECAUDACION).
    Patrones de campo frecuentes en A1 real: (i) casillas superiores con fecha/monto manuscritos, (ii) bloque termico lateral con lineas **Cedula Dep. / Serial / Monto / Fondos**, (iii) leyenda inferior tipo **PDP. 056**.
    Estos tres patrones pueden aparecer con texto tenue o parcialmente superpuesto; no descartes A si el nucleo Mercantil+0105+RAPI sigue claro.
    Extrae **fecha_pago**, **monto** y **numero_referencia** solo de digitos/texto visibles. Prioridad de referencia en A1: (1) linea **Serial:** larga (ej. 7400...), (2) codigo guionado con **DCME** y bloque **YYYYMMDD**, (3) si no hay serial legible pero hay numero de control impreso claramente asociado al deposito Mercantil en el mismo bloque operativo, usa ese valor completo. Nunca uses la cuenta **0105-...** como referencia.
    Si hay doble lectura por OCR (un serial tenue y otro mas nítido por contraste), usa la secuencia mas legible y continua; no mezcles digitos de dos lecturas.
    Prioridad de fecha en A1: (1) fecha de operacion impresa en tira/codigo guionado, (2) casilla **Fecha** del formulario si esta legible y coherente con el mismo comprobante. Si ambas existen y difieren, prioriza la impresa del bloque operativo.
    En fotos donde solo una de las dos fechas es claramente legible (tira o casilla), usa la legible sin forzar NA.
    Manuscritos (monto, fecha en casillas, depositante) solo si son legibles; si hay conflicto entre manuscrito e impreso, prioriza **impreso** del validador. Si el correo o la captura mezcla **varias** fotos y no hay **un** bloque Mercantil+RAPI completo -> **ninguno**.
    Palabra **RECAUDACIÓN** en el sello Mercantil **no** convierte el documento en otro banco: sigue siendo **imagen 1 (A)** si hay **Mercantil + 0105 + RAPI + DEPOSITO DIVISAS**. **No es imagen 4 (D)**: formato D es **Banco de Venezuela + cuenta 0102**; Mercantil **0105** aqui es siempre **A**, aunque el papel sea horizontal y el sello lleve "Secuencial Nro" u otras etiquetas que recuerden comprobantes BDV.
    Foto movil / borrosa: si reconoces claramente Mercantil + DEPOSITO DIVISAS + RAPI + cuenta 0105 + USD, intenta A (no "ninguno" por calidad si fecha/monto/referencia son razonablemente legibles). Patrones DP/Cédula en papel sirven solo para **clasificar** A vs B (ver REGLA CEDULA); no rellenes cedula en JSON desde la imagen.
    Si el formulario aparece totalmente girado (90/180/270) o con perspectiva, rota mentalmente y conserva A cuando las casillas clave sigan identificables.
  (A2) **Solo tira termica / comprobante de cajero Mercantil**: texto monoespaciado o vertical; lineas **Cedula Dep.**, **Cant. Billetes**, **Comision**, **Tasa**; cuenta tipo **0105-....-..-..........**; destino RAPI/RAPH-CREDIT + **RECAUDACION**; serial largo solo digitos (ej. 7403...) y/o cadena con guiones con bloque **YYYYMMDD**.
  Verificacion **sin inventar** (A2 / tira): antes de devolver A, comprueba en **los pixeles de esta pieza** al menos: (1) texto beneficiario **RAPI-CREDIT** (u variante OCR del Grupo 1), (2) **RECAUDACION** en **Fondos** o linea equivalente, (3) **USD** junto al monto, (4) cuenta que **empiece por 0105**, (5) **numero_referencia** y **fecha_pago** realmente legibles (serial **7400...** y/o bloque guionado con **DCME** y 2do grupo **YYYYMMDD** cuando exista). Si falta cualquiera de los datos obligatorios para JSON (fecha/monto/ref) -> **ninguno**; no completes por plantilla mental.
  Reconocimiento visual comun: cabecera o marca Banco Mercantil / MERCANTIL / "Mercantil, C.A." cuando aparece en (A1); en (A2) basta **0105** + RAPI + RECAUDACION en la tira.
  Beneficiario / empresa destino en la tira impresa: RAPI-CREDIT, C.A. o RAPI-CREDIT (misma familia que Grupo 1).
  Fondos / concepto impreso: RECAUDACION (u OCR sucio RECAUDACION).
  Moneda: checkbox o texto USD / dolares en el formulario; monto en USD en tira (asteriscos + NN,dd USD con coma decimal) o casilla manuscrita.
  Grupos equivalentes para esta variante: (1) RAPI-CREDIT como destino, (2) RECAUDACION en fondos, (3) USD, (4) cedula legible (impresa y/o manuscrita), (5) referencia: linea Serial larga digitos y/o codigo operacion con guiones YYYYMMDD en 2do bloque.
  Cuenta cliente en casillas o en tira (ej. 0105 0120 22 5120135978 o 0105-0120-22-5120135978) NO es numero_referencia; no confundir con serial de operacion. **0105** confirma institucion Mercantil para campo banco en JSON (ej. "Mercantil" o "Banco Mercantil").
  fecha_pago: usar fecha de la operacion en tira (2do bloque YYYYMMDD si aparece en el codigo guionado) o fecha manuscrita "31/3/2026" en el formulario si la tira es ilegible — una sola fecha coherente DD/MM/YYYY.
  Si cumple esta variante Mercantil, clasifica A (no "ninguno" por ser banco Mercantil; no B salvo que cumpla nucleo BNC completo de PASO 2).

FORMATO B — comprobante BNC de deposito a favor de RAPI-CREDIT (segunda plantilla valida; horizontal, tira vertical corta, o foto rotada):
  Plantilla tipica (reconoce aunque el orden de lineas varie un poco):
    - Esquina superior izquierda o cabecera: logo/texto BNC.
    - **Ref.** / **Ref:** / **Rif. N°** en cabecera o margen (numero de control; puede diferir en 1-3 digitos del **Serial** impreso).
    - Lineas tipo: Agencia: ... | Terminal: ... | Cajero: ... (nombres de cajero frecuentes).
    - Fecha y hora de operacion en una linea (ej. DD/MM/YYYY HH:MM:SS), a veces bloque derecho separado del bloque izquierdo (layout **dos columnas**).
    - Etiqueta **Serial:** seguida de digitos (muy frecuente **8-9 cifras**; no es obligatorio que sea ristra >12 ni que empiece en 7).
    - Cuenta del beneficiario con barras: patron ####/####/##/########## (ej. 0191/0127/48/2300080639).
    - Titular de la cuenta visible como RAPI-CREDIT, C.A. | RAPI-CREDIT C.A. | RAPI-CREDIT (misma familia que formato A pero aqui es CUENTA DESTINO en recibo BNC, no ticket de recaudacion).
    - Depositante: linea **DP:V-...** / **DP: E-...** con nombre, o linea **RIF: J-...** con nombre (persona juridica o empresa); en B el papel es recibo BNC, no ticket RECAUDACION Mercantil.
    - Monto (señal fuerte imagen 2): el importe en dolares CASI SIEMPRE va precedido de ASTERISCOS antes de los digitos y decimales,
      ej. **********122.00, *****96.00; suele acompañar texto tipo **Deposito Us$** | **Deposito US$** | Debito Us$ | Us$ | US$. Coma o punto decimal segun impresion; extrae el valor numerico.
      Si ves esta cortina de asteriscos + decimales en contexto BNC, clasifica B y extrae solo la cifra (ej. 122.00 USD).
    - Fondo con patron gris repetido (floral/hojas) y texto impreso tipo matriz de puntos; **sello azul** de agencia
      ("RECIBIDO CAJERO", fecha, "Deposito U.S$", nombre sucursal) — refuerza B; **no** confundir con formato D (BDV): aqui sigue habiendo **BNC + 0191/...**.
  VARIANTE B1 — **Sello azul grande** cubriendo parte del texto: si ves BNC + 0191 + RAPI + monto con asteriscos, sigue siendo **B** aunque el sello tape lineas; lee Ref/Serial/Fecha en zonas visibles.
  VARIANTE B2 — **Fondo gris repetido BNC (marca de agua)**: el recibo puede verse "lavado", con letras tenues por sobreexposicion o compresion. Si aun se distinguen
    BNC/BancoNacionaldeCredito + cuenta 0191/... + RAPI-CREDIT + Deposito Us$ + monto con asteriscos + bloque Ref/Serial/fecha, clasifica **B**.
  VARIANTE B3 — **Foto sobre mesa o mano con perspectiva**: aunque el ticket este inclinado o con distorsion trapezoidal, clasifica **B** si el nucleo estructural existe.
    No penalices por bordes negros, sombras de dedos o marco del telefono.
  Criterio B (minimo): BNC + cuenta con slashes tipo 0191/... + RAPI-CREDIT como beneficiario/titular
    + indicio claro de dolares (Us$, US$, USD, o monto con **... y decimales tipo deposito) + Agencia o Terminal/Cajero o Serial o Ref.
  NO es B si es otro banco, solo captura de app, o BNC sin RAPI-CREDIT en la zona de cuenta/beneficiario.

  Diferencia A vs B: A = ticket RAPI-CREDIT RECAUDACION; B = recibo BNC donde RAPI-CREDIT es titular de cuenta destino.
    Ya decidiste con PASO 2-4 arriba; aqui el detalle de plantilla.

Resumen discriminadores (cruce con PASO 4): serial 2do bloque YYYYMMDD (ticket Mercantil con guiones) -> A;
  **BNC + 0191/... + RAPI + Ref o Serial** (digitos cortos tipicos de cajero) -> **B**; sello azul RECIBIDO CAJERO sin cambiar B;
  cuenta que empieza en **0105** + RAPI + RECAUDACION (tira o formulario) -> **A Mercantil**, no B;
  ristra larga 7400... + Mercantil + DEPOSITO DIVISAS + RAPI + RECAUDACION -> A (variante Mercantil), no confundir con B solo por digitos largos.
  Cedula+nombre misma linea DP:...-NOMBRE en ticket vertical RECAUDACION -> A; misma linea DP en recibo **BNC horizontal** -> B; monto *...*122.00 con BNC -> fuerte B.

DESCARTE (refuerzo PASO 1): sin RAPI-CREDIT ni BNC ni nucleo Binance C -> ninguno.
  Ticket A completo pero sin recibo BNC -> A si grupos 1-5 OK; si falta grupo obligatorio de A -> ninguno.
  Recibo BNC + RAPI titular + dolares -> B aunque no diga literal "Deposito Us$".
  Pantalla Binance Pay nucleo C -> C aunque no haya RAPI-CREDIT en la captura.

=== DETALLE FORMATO A ===
**Ticket vertical** (terminal): fuente monoespaciada; los 5 grupos clasicos deben verse; el margen
"Copia"/SPDP ayuda pero no sustituye empresa+recaudacion+USD+cedula+monto/serial.
**Papeleta Mercantil DEPOSITO DIVISAS (A1)**: no apliques la regla de "DP y nombre en la misma linea" del ticket; usa casillas y tira del validador segun VARIANTE MERCANTIL.
  Normalizacion practica OCR en A1: acepta variantes ruidosas como "Merca ntil", "DEPOSITO DIVISAS" sin tilde, "RAPI-CREDI", "RECAUDACI0N" (con cero), "Cedula Dep" sin acento.
  No bajes a ninguno por errores menores de OCR si el layout estructural Mercantil A1 es inequívoco.
cedula: en JSON **siempre "NA"** (REGLA CEDULA). Para **clasificar** A vs B puedes usar DP:, Cédula Dep., casillas de cedula en papel, etc.; nunca copies cedula al JSON.
numero_referencia: la cadena completa del serial con guiones tal como en el comprobante; verifica que el segundo
  bloque separado por guiones sea 8 digitos fecha (YYYYMMDD). Si OCR pierde guiones, reconstruye la estructura
  minima para que el 2do segmento sea la fecha legible.
  En VARIANTE MERCANTIL: si existe "Serial:" con solo digitos (13+ cifras tipico), usa esa cadena completa como numero_referencia; si ademas hay 9213-YYYYMMDD-...-DCME-..., el Serial largo tiene prioridad.
monto: en Mercantil con coma decimal (96,00) devuelve equivalente con punto para el JSON si el esquema lo requiere (ej. 96.00 USD).

=== DETALLE FORMATO B ===
Prioriza la plantilla BNC anterior (horizontal, vertical, con o sin sello azul de ventanilla).
  Normalizacion practica para OCR BNC: acepta variantes como "Deposi to Us$", "BancoNacionaldeCredito", "RAPI-CREDI", "RAPI-CREDIT C.A" y espacios/guiones inconsistentes
  como equivalentes del mismo campo, sin bajar formato a ninguno cuando el contexto estructural sea claramente BNC.
  numero_referencia: (1) Si aparece **Ref:** / **Ref.** / **Referencia** con numero de control claro, usalo como primera opcion (ej. 141810437, 150927688).
  (2) Si no hay Ref legible, usa el valor junto a **Serial:** (ej. 141810434, 150927684 — suelen ser **8-9 digitos**).
  (3) Si hay **Ref: NF 000001327** u otro formato con prefijos, copia la cadena completa legible.
  (4) Solo si ninguno de los anteriores es usable y hay una ristra **muy larga** solo digitos (>12) en contexto BNC, usala.
  Si hay doble lectura de Ref (impreso tenue + trazo mas oscuro), usa la lectura mas nítida; no combines digitos de ambas.
  No uses el numero de cuenta 0191/... como numero_referencia.
  cedula en JSON: siempre "NA" (REGLA CEDULA); lineas DP: o RIF: sirven solo para clasificar B vs A.
  monto: patron tipico imagen 2 = asteriscos seguidos de NN.mm o NN,mm; extrae NN.mm y devuelve ej. 122.00 USD (sin asteriscos en JSON).
  fecha_pago: fecha y hora impresas de la operacion (una sola cadena legible DD/MM/YYYY HH:MM:SS si hay hora).

=== DETALLE FORMATO D (imagen 4 / Banco de Venezuela BDV) ===
  Comprobante impreso de **Banco de Venezuela** (no BNC): deposito / transaccion a cuenta empresa en USD (titular impreso: **RAPI CREDIT**, **SOFT CREDIT C.A.** u otra razon en la linea de titular, siempre con **0102-...**).
  Incluye **tira vertical** (VARIANTE D1) y **hoja horizontal** (VARIANTE D2) con **franja DEPOSITOS/PAGOS/TARJETAS**: ambos son D si cumplen nucleo BDV + cuenta **0102** + titular + monto + **numero de operacion** (secuencial) legible.
  **Depositante en blanco**: si **Nombre del depositante** y **CI/RIF del depositante** estan vacios, **sigue siendo D**; rellena fecha_pago, monto y numero_referencia desde el comprobante.
  banco en JSON: "BDV" o "Banco de Venezuela" si se lee; si no, "NA" (el Excel usara BDV por defecto).
  monto: **Monto Total** / **Total Efectivo** / **Total Deposito** / monto en dolares segun linea impresa (coma decimal tipica); ignora linea en letras salvo para validar coherencia; si hay monto manuscrito y otro impreso, prioriza **impreso**.
  numero_referencia: valor junto a **SECUENCIAL NRO** / **Secuencial Nro** (conserva **ceros a la izquierda**, ej. 0000091316488). Si no hay etiqueta clara pero hay **par** numero largo+ceros / numero rojo en cabecera BDV, el **largo** es la referencia operativa.
    Si hay **segundo** numero en rojo mas corto, prioriza igualmente la forma **completa con ceros** del secuencial cuando sea legible; si solo uno es claro, usa ese.
    Si el secuencial esta parcialmente tapado por sello/manuscrito, permite usar el otro numero de operacion impreso mas legible del mismo bloque BDV (sin inventar ni mezclar cifras de campos distintos).
    En comprobantes rotados donde el **numero rojo** es el dato mas legible del bloque operativo, puede usarse como `numero_referencia` si pertenece claramente a la misma transaccion.
    Regla quirurgica prioritaria BDV: si **SECUENCIAL NRO** esta oculto/ilegible por sello o firma y el **numero rojo** de operacion (normalmente en cabecera/borde) es nitido y unico en el comprobante, usa ese numero rojo como `numero_referencia` antes de devolver `ninguno`.
    No usar: numero de cuenta 0102-..., montos, ni anotaciones manuscritas tipo "R.F-..." como unica referencia.
  fecha_pago: **Fecha** y **Hora** del comprobante (combinar en un solo texto legible DD/MM/YYYY si hay fecha; si hay hora, puede ir en el mismo campo o despues de espacio).
  cedula: siempre "NA" (incluso si **DATOS DEL DEPOSITANTE** o anotaciones manuscritas muestran CI/RIF — REGLA CEDULA).

=== DETALLE FORMATO C (imagen 3 / Binance Pay) ===
  Banco en Excel lo fija el sistema como BINANCE; no hace falta devolver campo banco en JSON.
  monto: lee cifra con USDT o USD (ej. 122 USDT -> "122.00 USDT" o "122 USDT" consistente).
  numero_referencia: copia entera el Id. de la orden (digitos; no omitas digitos por OCR).
  email_cliente: pagador/cliente si se ve en pantalla; no uses solo el correo corporativo del beneficiario (operaciones@empresa). Si no hay email del pagador, CONTEXTO_REMITE o "NA".
  fecha_pago: "NA". cedula: "NA".

=== EXTRACCION ===
A/B/D: fecha_pago, monto y numero_referencia desde la imagen/PDF. cedula SIEMPRE "NA" (sin excepcion): aplica a **imagen 1, 2 y 4** venga el binario **embebido o adjunto**.
C: igual: cedula SIEMPRE "NA" (**imagen 3**); no copies documento del pagador desde la captura.
Unificado: **ningun** formato (A/B/C/D) debe poner numero de cedula/RIF en "cedula" del JSON; el backend usa solo el remitente del correo.
  banco: nombre de la INSTITUCION del comprobante (como aparece: logo, cabecera, pie de pagina).
    Ejemplos: formato B con logo BNC -> "BNC" o "Banco Nacional de Credito"; variante Mercantil (DEPOSITO DIVISAS) -> "Mercantil" o "Banco Mercantil";
    formato D BDV -> "BDV" o "Banco de Venezuela";
    ticket RECAUDACION RAPI si ves nombre de banco en el ticket usalo; si solo dice RAPI sin banco legible -> "NA".
C: monto y numero_referencia desde la imagen; fecha_pago="NA"; cedula="NA"; email_cliente="NA".

FORMATO NR — comprobante bancario o de cajero **reconocible** (papel, tira, deposito, recaudacion, etc.) pero el **beneficiario / titular de la cuenta / empresa destino NO es RapiCredit** (ni RAPI-CREDIT, RAPI CREDIT, RAPICREDIT ni variantes OCR del Grupo 1) y **no** es nucleo C (Binance Pay):
  Usalo solo cuando en los pixeles se vea claramente un **deposito o recibo bancario** con monto o datos de operacion, pero el dinero va a **otra razon social** distinta de RapiCredit.
  Devuelve **exactamente** "monto":"NR" (literal NR, sin cifras inventadas). "cedula":"NA" y "email_cliente":"NA" (el backend usa el remitente del correo para la columna Cedula del Excel).
  Campo adicional **"monto_operacion"**: monto **numerico** de la operacion impresa en el comprobante (misma regla de decimales que A/B/D: coma o punto, sin texto inventado). Si el monto total no es legible con certeza, **"NA"**. El backend lo usa solo para intentar alta automatica en `pagos` (el Excel exportado sigue mostrando columna Monto = NR).
  "fecha_pago" y "numero_referencia": copia lo legible del comprobante; si no hay certeza, "NA".
  "banco": nombre corto si se lee en el papel (ej. Mercantil, BNC, BDV, Banesco); si no, "NA".
  **Prohibido** usar NR para fotos sin comprobante (selfie, logo, pantalla de app no bancaria, borrosa sin datos) -> en ese caso **ninguno**.
  **Prohibido** usar NR si el beneficiario **si** es RapiCredit: ahi es A, B o D segun las reglas ya definidas.

Salida: solo JSON, sin markdown.
  A/B/D: {"formato":"A"|"B"|"D","fecha_pago":"...","cedula":"NA","monto":"...","numero_referencia":"...","email_cliente":"NA","banco":"Mercantil"|"BNC"|"BDV"|"..."}
  C: {"formato":"C","fecha_pago":"NA","cedula":"NA","monto":"...","numero_referencia":"...","email_cliente":"NA","banco":"NA"}
  NR: {"formato":"NR","fecha_pago":"...|NA","cedula":"NA","monto":"NR","monto_operacion":"123.45"|"NA","numero_referencia":"...|NA","email_cliente":"NA","banco":"..."}
  ninguno: {"formato":"ninguno","fecha_pago":"NA","cedula":"NA","monto":"NA","numero_referencia":"NA","email_cliente":"NA","banco":"NA"}
""".strip()

# Estos formatos pasan a Drive/BD/etiquetas Gmail MERCANTIL + BNC + BINANCE + BNV (D = BDV; cedula en Excel por remitente De en clientes).
# NR = comprobante bancario reconocible pero NO a favor de RapiCredit (Excel: monto literal "NR").
PAGOS_GMAIL_FORMATOS_PLANTILLA: frozenset[str] = frozenset({"A", "B", "C", "D", "NR"})


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


# Una sola ejecución: registra opener HEIC/HEIF si pillow-heif está instalado (Render/Linux suele tener wheel).
_PAGOS_GMAIL_HEIF_INIT_DONE = False


def _ensure_pillow_heif_opener() -> None:
    """Registra pillow-heif para que PIL abra .heic/.heif; si no hay paquete o falla, no se reintenta."""
    global _PAGOS_GMAIL_HEIF_INIT_DONE
    if _PAGOS_GMAIL_HEIF_INIT_DONE:
        return
    _PAGOS_GMAIL_HEIF_INIT_DONE = True
    try:
        from pillow_heif import register_heif_opener

        register_heif_opener()
        logger.info(
            "[PAGOS_GMAIL] HEIC/HEIF: pillow-heif registrado; PIL puede normalizar .heic/.heif a JPEG"
        )
    except Exception as exc:
        logger.debug(
            "[PAGOS_GMAIL] pillow-heif no disponible (%s); HEIC seguirá con fallback a bytes crudos",
            exc,
        )


def _pil_image_to_rgb_for_jpeg(img):
    """
    JPEG no admite canal alpha. RGBA/LA o paleta con transparencia se componen sobre blanco.
    CMYK y otros modos se llevan a RGB para evitar errores al guardar.
    """
    from PIL import Image as _PIL

    if img.mode == "RGBA":
        bg = _PIL.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        return bg
    if img.mode == "LA":
        img = img.convert("RGBA")
        bg = _PIL.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        return bg
    if img.mode == "P":
        if "transparency" in img.info:
            img = img.convert("RGBA")
            bg = _PIL.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[3])
            return bg
        return img.convert("RGB")
    if img.mode == "CMYK":
        return img.convert("RGB")
    if img.mode == "L":
        return img
    if img.mode != "RGB":
        return img.convert("RGB")
    return img


def _build_image_part(
    file_content: bytes,
    filename: str,
    mime: str,
    max_long_edge: Optional[int] = None,
):
    """
    Convierte bytes en un Part de google.genai.
    Para imágenes: pasa por PIL para normalizar (JPEG). Para PDFs: bytes directos.

    max_long_edge: si se indica (p. ej. escáner Infopagos), reduce la imagen manteniendo
    proporción para acortar tiempo de red/API sin tocar PDFs.
    """
    from google.genai import types as _gtypes
    is_pdf = mime == "application/pdf" or filename.lower().endswith(".pdf")
    if is_pdf:
        return _gtypes.Part.from_bytes(data=file_content, mime_type=mime)
    _ensure_pillow_heif_opener()
    try:
        from PIL import Image as _PIL
        from PIL import ImageOps

        img = _PIL.open(io.BytesIO(file_content))
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass
        img = _pil_image_to_rgb_for_jpeg(img)
        if max_long_edge and max_long_edge > 0:
            w, h = img.size
            longest = max(w, h)
            if longest > max_long_edge:
                scale = max_long_edge / float(longest)
                nw = max(1, int(round(w * scale)))
                nh = max(1, int(round(h * scale)))
                try:
                    resample = _PIL.Resampling.LANCZOS  # type: ignore[attr-defined]
                except AttributeError:
                    resample = _PIL.LANCZOS  # type: ignore[attr-defined]
                img = img.resize((nw, nh), resample)
                logger.debug(
                    "[PAGOS_GMAIL] Gemini imagen reescalada para envío: %s %sx%s -> %sx%s",
                    filename,
                    w,
                    h,
                    nw,
                    nh,
                )
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=92, optimize=True)
        logger.debug("[PAGOS_GMAIL] Gemini PIL→JPEG OK: %s", filename)
        return _gtypes.Part.from_bytes(data=buf.getvalue(), mime_type="image/jpeg")
    except Exception as pil_err:
        logger.warning("[PAGOS_GMAIL] PIL falló (%s), bytes crudos para %s", pil_err, filename)
        return _gtypes.Part.from_bytes(data=file_content, mime_type=mime)


@lru_cache(maxsize=8)
def _gemini_client_cached(api_key: str):
    """Reutiliza Client por clave API (HTTP keep-alive / menos handshake TLS)."""
    from google import genai

    return genai.Client(api_key=api_key)


def _gemini_client(key: str):
    k = (key or "").strip()
    if not k:
        from google import genai

        return genai.Client(api_key="")
    return _gemini_client_cached(k)


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


def _pagos_gmail_ab_campos_imagen_completos(fields: Dict[str, str]) -> bool:
    """A/B/D: fecha, monto y referencia desde imagen; cedula la resuelve el backend (JSON con cedula NA)."""
    for k in ("fecha_pago", "monto", "numero_referencia"):
        s = (fields.get(k) or "").strip()
        if not s or s.upper() == PAGOS_NA:
            return False
    return True


def _pagos_gmail_ab_campos_imagen_completos_error_email_ab(fields: Dict[str, str]) -> bool:
    """Modo re-escaneo ERROR EMAIL: A o B con fecha/monto/ref + cedula legible o literal ERROR."""
    for k in ("fecha_pago", "monto", "numero_referencia"):
        s = (fields.get(k) or "").strip()
        if not s or s.upper() == PAGOS_NA:
            return False
    c = (fields.get("cedula") or "").strip()
    if not c or c.upper() == PAGOS_NA:
        return False
    return True


def _pagos_gmail_format_c_complete(fields: Dict[str, str]) -> bool:
    """Formato C: monto y referencia desde imagen; fecha, cedula y email_cliente NA (cliente/cédula por remitente en backend)."""
    fp = (fields.get("fecha_pago") or "").strip().upper()
    ce = (fields.get("cedula") or "").strip().upper()
    if fp != PAGOS_NA or ce != PAGOS_NA:
        return False
    for k in ("monto", "numero_referencia"):
        s = (fields.get(k) or "").strip()
        if not s or s.upper() == PAGOS_NA:
            return False
    return True


def _pagos_gmail_nr_campos_completos(fields: Dict[str, str]) -> bool:
    """NR: el modelo debe devolver monto literal NR (no inventar cifras de RapiCredit)."""
    m = (fields.get("monto") or "").strip().upper()
    return m == "NR"


def _is_na_pagos(v: Optional[str]) -> bool:
    s = (v or "").strip().upper()
    return (not s) or s == PAGOS_NA


def _diag_none_reason_pagos(
    fmt_raw: str,
    fields: Dict[str, str],
    raw_text: str,
) -> str:
    fmt_u = (fmt_raw or "").strip().upper()
    raw_lc = (raw_text or "").lower()
    if fmt_u in ("A", "B", "D"):
        miss = []
        if _is_na_pagos(fields.get("fecha_pago")):
            miss.append("fecha")
        if _is_na_pagos(fields.get("monto")):
            miss.append("monto")
        if _is_na_pagos(fields.get("numero_referencia")):
            miss.append("ref")
        if miss:
            if miss == ["ref"]:
                return "falto_ref"
            if miss == ["monto"]:
                return "falto_monto"
            if miss == ["fecha"]:
                return "falto_fecha"
            return "campos_incompletos_abd"
    if fmt_u == "C":
        miss = []
        if _is_na_pagos(fields.get("monto")):
            miss.append("monto")
        if _is_na_pagos(fields.get("numero_referencia")):
            miss.append("ref")
        if miss == ["ref"]:
            return "falto_ref"
        if miss == ["monto"]:
            return "falto_monto"
        if miss:
            return "campos_incompletos_c"
    if fmt_u == "NR":
        if (fields.get("monto") or "").strip().upper() != "NR":
            return "nr_monto_invalido"
    if any(k in raw_lc for k in ("borros", "ilegib", "desenfo", "bajo contraste", "contraste")):
        return "bajo_contraste_ilegible"
    if "refer" in raw_lc or " ref" in raw_lc:
        return "falto_ref"
    if "monto" in raw_lc:
        return "falto_monto"
    if "fecha" in raw_lc:
        return "falto_fecha"
    if fmt_u in ("A", "B", "C", "D", "NR"):
        return f"fmt_{fmt_u.lower()}_invalido"
    return "sin_plantilla"


def _parse_formato_y_pagos_json(
    text: str,
    remitente_from_header: Optional[str] = None,
    *,
    modo_error_email_ab: bool = False,
) -> Tuple[PagosGmailFormato, Dict[str, str]]:
    empty = _empty_result()
    empty["_diag_none_reason"] = "json_invalido"
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
        elif fmt_raw == "D":
            fmt = "D"
        elif fmt_raw == "NR":
            fmt = "NR"
        else:
            fmt = "ninguno"
        fields = {
            "fecha_pago": _normalize_to_na(data.get("fecha_pago", PAGOS_NA)),
            "cedula": _normalize_to_na(data.get("cedula", PAGOS_NA)),
            "monto": _normalize_to_na(data.get("monto", PAGOS_NA)),
            "monto_operacion": _normalize_to_na(data.get("monto_operacion", PAGOS_NA)),
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
            "monto_operacion": PAGOS_NA,
            "numero_referencia": PAGOS_NA,
            "email_cliente": PAGOS_NA,
            "banco": PAGOS_NA,
            "_diag_none_reason": "sin_plantilla",
        }
        if fmt == "ninguno":
            _out = na_fields.copy()
            _out["_diag_none_reason"] = _diag_none_reason_pagos(fmt_raw, fields, text)
            return fmt, _out
        if fmt == "C":
            fields["email_cliente"] = PAGOS_NA
            if not _pagos_gmail_format_c_complete(fields):
                _out = na_fields.copy()
                _out["_diag_none_reason"] = _diag_none_reason_pagos(fmt_raw, fields, text)
                return "ninguno", _out
            fields["banco"] = PAGOS_NA
            return fmt, fields
        if fmt == "NR":
            fields["cedula"] = PAGOS_NA
            fields["email_cliente"] = PAGOS_NA
            fields["monto"] = "NR"
            fields["monto_operacion"] = _normalize_to_na(data.get("monto_operacion", PAGOS_NA))
            if not _pagos_gmail_nr_campos_completos(fields):
                _out = na_fields.copy()
                _out["_diag_none_reason"] = _diag_none_reason_pagos(fmt_raw, fields, text)
                return "ninguno", _out
            return fmt, fields
        if fmt in ("A", "B") and modo_error_email_ab:
            ce = (fields.get("cedula") or "").strip()
            if (not ce) or ce.upper() == PAGOS_NA:
                fields["cedula"] = "ERROR"
            elif ce.upper() == "ERROR":
                fields["cedula"] = "ERROR"
            if not _pagos_gmail_ab_campos_imagen_completos_error_email_ab(fields):
                _out = na_fields.copy()
                _out["_diag_none_reason"] = _diag_none_reason_pagos(fmt_raw, fields, text)
                return "ninguno", _out
            fields["email_cliente"] = PAGOS_NA
            return fmt, fields
        # A, B o D: ignorar cedula del modelo; solo fecha/monto/ref desde imagen
        fields["cedula"] = PAGOS_NA
        if not _pagos_gmail_ab_campos_imagen_completos(fields):
            _out = na_fields.copy()
            _out["_diag_none_reason"] = _diag_none_reason_pagos(fmt_raw, fields, text)
            return "ninguno", _out
        fields["email_cliente"] = PAGOS_NA
        return fmt, fields
    except (json.JSONDecodeError, TypeError):
        return "ninguno", empty.copy()


def classify_and_extract_pagos_gmail_attachment(
    file_content: bytes,
    filename: str,
    api_key: Optional[str] = None,
    remitente_correo_header: Optional[str] = None,
    origen_binario: Optional[str] = None,
    *,
    modo_error_email_ab: bool = False,
) -> Tuple[PagosGmailFormato, Dict[str, str]]:
    """
    Clasifica el comprobante en formato A (RAPI-CREDIT terminal), B (BNC), C (Binance Pay), D (BDV imagen 4), NR (no RapiCredit) o ninguno,
    y extrae campos desde el archivo. Por defecto la cédula no sale del modelo (pipeline por email De en clientes).
    Con **modo_error_email_ab=True** (re-escaneo ERROR EMAIL): para A y B el modelo devuelve cédula desde la imagen o "ERROR".
    """
    key = api_key or getattr(settings, "GEMINI_API_KEY", None)
    if not key:
        logger.warning("[PAGOS_GMAIL] GEMINI_API_KEY no configurado; formato=ninguno")
        return "ninguno", _empty_result(PAGOS_NA)
    mime = get_mime_type(filename)
    image_part = _build_image_part(file_content, filename, mime)
    model_name = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
    prompt_text = GEMINI_PAGOS_GMAIL_FORMATO_Y_EXTRACCION
    if modo_error_email_ab:
        prompt_text = prompt_text + "\n\n" + GEMINI_PAGOS_GMAIL_MODO_ERROR_EMAIL_AB.strip()
    if origen_binario:
        prompt_text = (
            f"ORIGEN_DEL_BINARIO: {origen_binario}\n"
            "embebida = imagen o PDF mostrado en el cuerpo del correo (inline, CID, multipart related, data URL en HTML, "
            "o parte MIME sin Content-Disposition: attachment).\n"
            "adjunta = archivo descargable clasico (PDF, JPG, PNG, WEBP, HEIC, etc.).\n"
            "reenvio_eml = imagen/PDF extraido de un correo .eml reenviado.\n"
            "mime_recorrido = otra parte image/PDF del arbol MIME.\n"
            "Si el adjunto era un PDF de varias paginas, el backend ya te envia UNA sola pagina por peticion.\n\n"
            + prompt_text
        )
    contents: list = [prompt_text, image_part]
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
                    text,
                    remitente_from_header=remitente_correo_header,
                    modo_error_email_ab=modo_error_email_ab,
                )
                if fmt not in PAGOS_GMAIL_FORMATOS_PLANTILLA:
                    _none_reason = (fields.get("_diag_none_reason") or "sin_plantilla").strip()
                    fmt = "ninguno"
                    fields = {
                        "fecha_pago": PAGOS_NA,
                        "cedula": PAGOS_NA,
                        "monto": PAGOS_NA,
                        "numero_referencia": PAGOS_NA,
                        "email_cliente": PAGOS_NA,
                        "banco": PAGOS_NA,
                        "_diag_none_reason": _none_reason,
                    }
                logger.info(
                    "[PAGOS_GMAIL] Gemini formato=%s fecha=%s cedula=%s monto=%s ref=%s email=%s banco=%s none_reason=%s",
                    fmt,
                    fields.get("fecha_pago"),
                    fields.get("cedula"),
                    fields.get("monto"),
                    fields.get("numero_referencia"),
                    fields.get("email_cliente"),
                    fields.get("banco"),
                    fields.get("_diag_none_reason", ""),
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
        "monto_operacion": PAGOS_NA,
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
    """Detecta 503/UNAVAILABLE/timeouts de Gemini (alta demanda o peticion demasiado larga)."""
    msg = (getattr(exc, "message", "") or str(exc)) if exc else ""
    low = msg.lower()
    return (
        "503" in msg
        or "unavailable" in low
        or "high demand" in low
        or "timed out" in low
        or "timeout" in low
        or "deadline" in low
    )


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
        # 429 y 503 pueden tener distinto max de reintentos: el bucle debe permitir el mayor.
        _max_gemini_attempts = max(GEMINI_RATE_LIMIT_MAX_RETRIES, GEMINI_SERVER_ERROR_MAX_RETRIES) + 1
        for attempt in range(_max_gemini_attempts):
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
        if _is_server_error_503(e) or _is_rate_limit_error(e):
            logger.warning("[COBROS] Gemini compare_form_with_image (transitorio): %s", str(e)[:800])
        else:
            logger.exception("Gemini compare_form_with_image: %s", e)
        default_result["comentario"] = str(e)[:500]
        return default_result


# ── Cobros / Infopagos: escáner (solo imagen → sugerencia de campos del formulario) ──

GEMINI_ESCANER_INFOPAGOS_PROMPT = """Eres un asistente de lectura de comprobantes de pago (Venezuela: bancos, Pago Móvil, Zelle, Binance Pay, recibos de ventanilla, etc.).

CONTEXTO (cédula del DEUDOR en el sistema — el cliente al que se le registra el pago; NO la confundas con la del depositante en el papel):
  "{cedula_deudor}"

REFERENCIA DE CALENDARIO (solo coherencia; no inventes fechas que no estén en el comprobante):
  - Fecha de hoy en Venezuela (America/Caracas), para comprobar que la operación no quede en el futuro: **{fecha_hoy_iso}**

TAREA: Lee la imagen o PDF adjunto y extrae SOLO lo que aparezca con claridad en el comprobante para rellenar un formulario de "Infopagos" con estos campos:
  - fecha_pago: fecha de la operación en el comprobante. Devuélvela como cadena en formato **YYYY-MM-DD** si puedes inferir año/mes/día; si solo hay día/mes sin año razonable, deja fecha_pago vacía "".
  - institucion_financiera: nombre corto del banco o entidad (ej. BNC, Mercantil, Banesco, BDV, BINANCE, Pago Móvil). Máximo 100 caracteres.
  - numero_operacion: número o código que identifica la transacción (Serial, Ref, Nº operación, referencia, código, ID de orden en Binance, etc.). Sin etiquetas largas: solo el valor. Máximo 100 caracteres.
  - monto: número decimal con punto como separador decimal (ej. 150.25). Si hay varios montos, el del pago principal al beneficiario. Si no es legible, usa null.
  - moneda: exactamente **BS** o **USD** (USDT, $ en contexto divisa fuerte, "Dólares", Binance Pay en USDT → USD).
  - cedula_pagador_en_comprobante: si en el comprobante aparece claramente la cédula del depositante (DP:, CI, RIF, etc.), devuélvela normalizada como una sola cadena tipo V12345678 (una letra V/E/J/G y dígitos sin ceros de más a la izquierda después de la letra). Si no aparece o hay duda, cadena vacía "".
  - notas: una frase corta opcional sobre calidad de lectura o ambigüedades (máx 300 caracteres); puede ser "".

REGLAS:
  - No inventes datos: si un campo no está legible, usa "" o null según el tipo.
  - No copies el correo ni datos que no estén en el comprobante.
  - FECHA OBLIGATORIA DESDE IMAGEN/PDF: `fecha_pago` debe salir del propio comprobante (línea Fecha, Fecha/Hora, fecha del bloque de transacción).
  - Prohibido usar fecha del correo, asunto, metadata del archivo, nombre del archivo o contexto externo para `fecha_pago`.
  - Si hay dos fechas en el comprobante (ej. sello y fecha transacción), prioriza la fecha del bloque principal de la operación/transferencia.
  - FORMATO VENEZOLANO / AMBIGÜEDAD: en boletos y apps locales casi siempre verás **día/mes/año** (o día-mes-año). Si ves **6 dígitos seguidos sin separadores** (ej. 191226), no asumas YYMMDD si con ello la operación quedaría **años incoherentes** respecto a otras fechas visibles del mismo boleto (sello, vigencia, año impreso, texto “202x”) o **en el futuro** respecto a {fecha_hoy_iso}. En ese caso prefiere la lectura **DDMMYY** (día/mes/año de dos dígitos) cuando encaje con el resto del comprobante; si sigue habiendo duda razonable, devuelve `fecha_pago` "" y explica en `notas`.
  - La fecha de operación inferida **no puede ser posterior** a {fecha_hoy_iso}; si una lectura lleva a futuro, corrige interpretación o deja "".
  - Si la fecha no es legible con suficiente certeza, deja `fecha_pago` como "" y explícitalo en `notas`.
  - Responde ÚNICAMENTE con un objeto JSON válido, sin markdown ni texto extra, con exactamente estas claves:
  fecha_pago, institucion_financiera, numero_operacion, monto, moneda, cedula_pagador_en_comprobante, notas
"""


def _parse_monto_escaner(val: Any) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        if isinstance(val, float) and (val != val or val == float("inf")):  # NaN / inf
            return None
        return float(val)
    s = str(val).strip().replace(" ", "").replace("Bs.", "").replace("Bs", "").replace("USD", "").replace("US$", "").replace("$", "")
    if not s or s.lower() in ("na", "n/a", "-"):
        return None
    # Formato latino 1.234,56
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2:
            s = parts[0].replace(".", "") + "." + parts[1]
        else:
            s = s.replace(",", ".")
    try:
        n = float(s)
        if n != n or n == float("inf"):
            return None
        return round(n, 2)
    except (TypeError, ValueError):
        return None


def _parse_fecha_escaner(val: Any) -> Optional[date]:
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() in ("na", "n/a", "-", ""):
        return None
    # ISO 8601 con hora: 2026-04-21T15:01:44 o ...Z
    if "T" in s[:29] and re.match(r"^\d{4}-\d{2}-\d{2}T", s):
        s = s.split("T", 1)[0].strip()
    # YYYY-MM-DD o YYYY/MM/DD (primeros 10 caracteres)
    s10 = s[:10]
    try:
        if len(s10) >= 10 and s10[4] in "-/" and s10[7] in "-/" and s10[4] == s10[7]:
            y, m, d = int(s10[0:4]), int(s10[5:7]), int(s10[8:10])
            return date(y, m, d)
    except (ValueError, TypeError):
        pass
    # dd/mm/yyyy o dd-mm-yyyy (año 4 cifras al final)
    m = re.match(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$", s)
    if m:
        try:
            d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            return date(y, mo, d)
        except ValueError:
            return None
    # dd.mm.yy o dd/mm/yy (año 2 cifras): heurística 20xx si yy < 70, si no 19xx
    m2 = re.match(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{2})$", s)
    if m2:
        try:
            d, mo, yy = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
            y = 2000 + yy if yy < 70 else 1900 + yy
            return date(y, mo, d)
        except ValueError:
            return None
    return None


def extract_infopagos_campos_desde_comprobante(
    cedula_deudor_contexto: str,
    image_bytes: bytes,
    filename: str = "comprobante.jpg",
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Solo lectura OCR/visión: sugiere campos del formulario Infopagos a partir del comprobante.
    No persiste nada. Requiere GEMINI_API_KEY.
    Retorna dict con ok, y campos sugeridos o error.
    """
    key = api_key or getattr(settings, "GEMINI_API_KEY", None)
    out_err: Dict[str, Any] = {
        "ok": False,
        "error": "Gemini no configurado o clave vacía.",
        "fecha_pago": None,
        "institucion_financiera": "",
        "numero_operacion": "",
        "monto": None,
        "moneda": "BS",
        "cedula_pagador_en_comprobante": "",
        "notas": "",
    }
    if not key or not str(key).strip():
        logger.warning("[ESCANER] GEMINI_API_KEY no configurado.")
        return out_err

    ctx = (cedula_deudor_contexto or "").strip() or "(no indicada)"
    from app.services.tasa_cambio_service import fecha_hoy_caracas

    hoy_iso = fecha_hoy_caracas().isoformat()
    prompt = (
        GEMINI_ESCANER_INFOPAGOS_PROMPT.replace("{cedula_deudor}", ctx)
        .replace("{fecha_hoy_iso}", hoy_iso)
    )

    model_name = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
    mime = get_mime_type(filename)
    try:
        from google import genai
        from google.genai import types

        client = _gemini_client(key)
        # Lado más largo acotado (solo escáner): menos bytes hacia Gemini; PDF sin cambios.
        image_part = _build_image_part(image_bytes, filename, mime, max_long_edge=2400)
        _max_gemini_attempts = max(GEMINI_RATE_LIMIT_MAX_RETRIES, GEMINI_SERVER_ERROR_MAX_RETRIES) + 1
        last_error: Optional[Exception] = None
        for attempt in range(_max_gemini_attempts):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[prompt, image_part],
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        # Respuesta corta (JSON); evita respuestas largas innecesarias del modelo.
                        max_output_tokens=2048,
                    ),
                )
                text = (response.text or "").strip()
                json_str = _find_json_object(text)
                if not json_str:
                    m = re.search(r"\{[^{}]*\}", text, re.DOTALL)
                    json_str = m.group(0) if m else None
                if not json_str:
                    return {
                        "ok": False,
                        "error": "No se pudo interpretar la respuesta del modelo.",
                        "fecha_pago": None,
                        "institucion_financiera": "",
                        "numero_operacion": "",
                        "monto": None,
                        "moneda": "BS",
                        "cedula_pagador_en_comprobante": "",
                        "notas": (text or "")[:300],
                    }
                data = json.loads(json_str)
                mon_raw = (data.get("moneda") or "BS").strip().upper()
                if mon_raw in ("USD", "USDT", "$", "DOLARES", "DÓLARES", "DIVISA") or "BINANCE" in mon_raw:
                    mon_norm = "USD"
                else:
                    mon_norm = "BS"

                inst = str(data.get("institucion_financiera") or "").strip()[:100]
                num_op = str(data.get("numero_operacion") or "").strip()[:100]
                fecha = _parse_fecha_escaner(data.get("fecha_pago"))
                monto = _parse_monto_escaner(data.get("monto"))
                ced_pag = str(data.get("cedula_pagador_en_comprobante") or "").strip()[:30]
                notas = str(data.get("notas") or "").strip()[:300]

                return {
                    "ok": True,
                    "error": None,
                    "fecha_pago": fecha,
                    "institucion_financiera": inst,
                    "numero_operacion": num_op,
                    "monto": monto,
                    "moneda": mon_norm,
                    "cedula_pagador_en_comprobante": ced_pag,
                    "notas": notas,
                }
            except Exception as e:
                last_error = e
                if _is_rate_limit_error(e) and attempt < GEMINI_RATE_LIMIT_MAX_RETRIES:
                    delay = _extract_retry_seconds(e)
                    logger.warning("[ESCANER] Gemini 429, reintento %d en %ds", attempt + 1, delay)
                    time.sleep(delay)
                elif _is_server_error_503(e) and attempt < GEMINI_SERVER_ERROR_MAX_RETRIES:
                    delay = GEMINI_SERVER_ERROR_RETRY_DELAY + (attempt * 5)
                    logger.warning("[ESCANER] Gemini 503, reintento %d en %ds", attempt + 1, delay)
                    time.sleep(delay)
                else:
                    raise
        return {
            "ok": False,
            "error": str(last_error)[:500] if last_error else "Error desconocido.",
            "fecha_pago": None,
            "institucion_financiera": "",
            "numero_operacion": "",
            "monto": None,
            "moneda": "BS",
            "cedula_pagador_en_comprobante": "",
            "notas": "",
        }
    except Exception as e:
        logger.exception("[ESCANER] extract_infopagos_campos_desde_comprobante: %s", e)
        return {
            "ok": False,
            "error": str(e)[:500],
            "fecha_pago": None,
            "institucion_financiera": "",
            "numero_operacion": "",
            "monto": None,
            "moneda": "BS",
            "cedula_pagador_en_comprobante": "",
            "notas": "",
        }

