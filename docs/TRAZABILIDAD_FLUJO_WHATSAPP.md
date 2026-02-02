# Trazabilidad del flujo WhatsApp (cobranza) — Paso a paso

Este documento describe el flujo completo del bot de cobranza por WhatsApp con criterios de trazabilidad: en cada paso se indica **qué se persiste**, **qué se registra en logs** y **cómo verificar** que el flujo está bien armado.

---

## 1. Entrada del mensaje (webhook)

| Paso | Dónde | Qué ocurre | Trazabilidad |
|------|--------|------------|--------------|
| **1.1** | `POST /api/v1/whatsapp/webhook` | Meta envía el payload. Se verifica firma (si `app_secret` configurado). | **Log:** `"Webhook recibido de WhatsApp: whatsapp_business_account"`. Si firma inválida: `"Firma del webhook inválida"` (403). |
| **1.2** | Mismo endpoint | Se valida `object == "whatsapp_business_account"`. Se recorren `entry` → `changes` → `value.messages`. | **Log:** Si tipo no soportado: `"Webhook recibido de objeto desconocido"`. Respuesta: `WhatsAppResponse(success, message, message_id)`. |
| **1.3** | `WhatsAppService.process_incoming_message()` | Se despacha por tipo: `text` → `_process_text_cobranza`, `image` → `_process_image_message`. | **Log:** `"Procesando mensaje WhatsApp - ID: ..., From: ..., Type: ..."`. **Persistencia:** Ninguna aún (solo entrada en memoria). |

**Criterio de verificación:** En logs del backend debe aparecer un `"Procesando mensaje WhatsApp"` por cada mensaje entrante; si no, revisar URL del webhook en Meta y que el servicio esté levantado.

---

## 2. Historial de mensajes (todos los mensajes)

| Paso | Dónde | Qué ocurre | Trazabilidad |
|------|--------|------------|--------------|
| **2.1** | `guardar_mensaje_whatsapp(db, telefono, "INBOUND", body, type)` | Se guarda **cada mensaje entrante** (texto o imagen) antes de procesar el flujo. | **Persistencia:** tabla `mensaje_whatsapp`: `telefono`, `direccion=INBOUND`, `body`, `message_type`, `timestamp`. |
| **2.2** | Después de obtener `response_text` | Se guarda **cada respuesta del bot** (texto enviado al usuario). | **Persistencia:** tabla `mensaje_whatsapp`: `direccion=OUTBOUND`, `body=response_text`. |

**Criterio de verificación:** En la UI de Comunicaciones, para un teléfono dado debe verse la secuencia INBOUND → OUTBOUND en orden temporal. Consultar `mensaje_whatsapp` por `telefono` normalizado (solo dígitos).

---

## 3. Flujo de texto (cobranza): estados y transiciones

El estado de la conversación vive en **`conversacion_cobranza`**: `estado`, `cedula`, `nombre_cliente`, `intento_foto`, `intento_confirmacion`, `observacion`, `updated_at`.

### 3.1 Primera vez o conversación obsoleta

| Paso | Condición | Acción | Persistencia / Log |
|------|-----------|--------|--------------------|
| **3.1.1** | No existe `ConversacionCobranza` para el teléfono | Se crea fila: `estado=esperando_cedula`, `intento_foto=0`, `intento_confirmacion=0`. | **BD:** `conversacion_cobranza` INSERT. |
| **3.1.2** | Si el texto parece "otra información" (ej. "quiero hablar con alguien") | No se cambia estado; se responde con teléfono de atención. | **Log:** ninguno específico. **Respuesta:** `MENSAJE_OTRA_INFORMACION`. |
| **3.1.3** | Si no pide otra información | Se responde bienvenida y se pide cédula. | **Respuesta:** `MENSAJE_BIENVENIDA`. Estado sigue `esperando_cedula`. |
| **3.1.4** | Existe conversación pero `updated_at` &gt; 24 h | Se llama `_reiniciar_como_nuevo_caso`: estado → `esperando_cedula`, se limpian cédula, nombre, intentos, observación. | **BD:** `conversacion_cobranza` UPDATE. **Log:** `"Conversación ... reiniciada como nuevo caso (inactividad > 24 h)."` |

**Criterio de verificación:** Tras 24 h sin mensajes, el siguiente mensaje debe recibir de nuevo la bienvenida y pedido de cédula. En BD, `conversacion_cobranza.updated_at` debe actualizarse en cada interacción.

### 3.2 Estado `esperando_cedula`

| Paso | Condición | Acción | Persistencia / Log |
|------|-----------|--------|--------------------|
| **3.2.1** | Texto no es cédula válida (E/J/V + 6–11 dígitos) | Si parece "otra información" → respuesta teléfono; si no → mensaje cédula inválida. | **Respuesta:** `MENSAJE_OTRA_INFORMACION` o `MENSAJE_CEDULA_INVALIDA`. Estado sigue `esperando_cedula`. |
| **3.2.2** | Texto es cédula válida | Se normaliza cédula, se busca nombre en `clientes`. Se actualiza conversación: `cedula`, `nombre_cliente`, `estado=esperando_confirmacion`, `intento_confirmacion=1`, `intento_foto=0`. | **BD:** `conversacion_cobranza` UPDATE. **Respuesta:** `MENSAJE_CONFIRMACION` (con nombre) o `MENSAJE_CONFIRMACION_SIN_NOMBRE`. |

**Criterio de verificación:** Tras enviar una cédula válida (ej. E1234567), en BD debe quedar `estado=esperando_confirmacion`, `cedula` y opcionalmente `nombre_cliente`. El usuario debe recibir el mensaje de confirmación.

### 3.3 Estado `esperando_confirmacion`

| Paso | Condición | Acción | Persistencia / Log |
|------|-----------|--------|--------------------|
| **3.3.1** | Usuario responde "Sí" (o equivalente) | `estado=esperando_foto`, `intento_foto=0`, `intento_confirmacion=0`. | **BD:** UPDATE. **Respuesta:** `MENSAJE_GRACIAS_PIDE_FOTO`. |
| **3.3.2** | Usuario responde "No" | Se reinicia: `estado=esperando_cedula`, se limpia cédula y nombre. | **BD:** UPDATE. **Respuesta:** `MENSAJE_VUELVE_CEDULA`. |
| **3.3.3** | Usuario escribe otra cosa (no Sí/No) | Si parece "otra información" → teléfono. Si no, se incrementa `intento_confirmacion`. Si `intento_confirmacion >= 3` → se pone `observacion=No confirma identidad`, `estado=esperando_foto` y se pide foto. Si &lt; 3 → se pide de nuevo Sí/No. | **BD:** UPDATE (intento y/o estado). **Respuesta:** `MENSAJE_RESPONDE_SI_NO` o `MENSAJE_CONTINUAMOS_SIN_CONFIRMAR`. |

**Criterio de verificación:** Tras "Sí", estado debe ser `esperando_foto`. Tras "No", estado debe volver a `esperando_cedula`. Tras 3 respuestas que no son Sí/No, estado debe pasar a `esperando_foto` y `observacion` debe quedar con "No confirma identidad".

### 3.4 Estado `esperando_foto` (usuario escribe texto)

| Paso | Condición | Acción | Persistencia / Log |
|------|-----------|--------|--------------------|
| **3.4.1** | Cualquier texto | Si parece "otra información" → teléfono. Si no, se recuerda que envíe foto (con nombre si existe). | **Respuesta:** `MENSAJE_OTRA_INFORMACION` o recordatorio de foto. Estado no cambia. |

**Criterio de verificación:** Mientras esté en `esperando_foto`, si el usuario escribe texto (que no sea "otra información"), debe recibir el recordatorio de enviar la foto; el estado sigue siendo `esperando_foto`.

---

## 4. Flujo de imagen (papeleta)

### 4.1 Sin conversación o estado no listo para foto

| Paso | Condición | Acción | Trazabilidad |
|------|-----------|--------|--------------|
| **4.1.1** | No existe conversación para el teléfono | Se pide cédula (bienvenida). | **Respuesta:** `MENSAJE_BIENVENIDA`. No se persiste imagen. |
| **4.1.2** | Conversación obsoleta (&gt; 24 h) | Se reinicia como nuevo caso y se pide cédula. | **BD:** `_reiniciar_como_nuevo_caso`. **Respuesta:** `MENSAJE_BIENVENIDA`. **Log:** reinicio. |
| **4.1.3** | `estado=esperando_cedula` | Se pide cédula. | **Respuesta:** `MENSAJE_BIENVENIDA`. |
| **4.1.4** | `estado=esperando_confirmacion` | No se pide cédula de nuevo; se pide confirmar primero (Sí/No) y luego foto. | **Respuesta:** `MENSAJE_PRIMERO_CONFIRMA_LUEGO_FOTO`. |

**Criterio de verificación:** Si el usuario envía una foto antes de confirmar, no debe volver a pedirse la cédula; debe pedirse "Primero confirma con Sí o No...".

### 4.2 Descarga y evaluación de la imagen (`estado=esperando_foto`)

| Paso | Dónde | Qué ocurre | Trazabilidad |
|------|--------|------------|--------------|
| **4.2.1** | Meta API | Se descarga la imagen con el token de WhatsApp. | **Log:** Si falla: `"Error descargando imagen: ..."`. No se persiste nada. |
| **4.2.2** | `intento_foto` | Se incrementa `intento_foto` (1, 2 o 3). | Se usa en el siguiente paso. |
| **4.2.3** | OCR (Vision) | `get_full_text(image_bytes)` para texto completo (para la IA). | **Log:** Si falla: `"OCR texto para IA: ..."` (debug). |
| **4.2.4** | IA | `evaluar_imagen_y_respuesta(ocr_text, cedula, db)` → `aceptable`, `mensaje_ia`. Si IA falla, fallback por claridad (ej. 50 caracteres). | **Log:** Si fallback: `"IA imagen falló, usando fallback por claridad: ..."`. |
| **4.2.5** | Imagen no aceptada y intento &lt; 3 | Se responde con `mensaje_ia` (o mensaje de reintento). Se hace commit de `intento_foto` y `updated_at`. | **BD:** `conversacion_cobranza` UPDATE. **Respuesta:** mensaje de "no válida" o pedir otra foto. **Log:** `"Foto papeleta no aceptada por IA (intento X/3); respuesta: ..."`. |

**Criterio de verificación:** En logs debe verse el intento (1, 2 o 3) cuando la imagen no es aceptada. En BD, `conversacion_cobranza.intento_foto` debe coincidir con el número de intentos de foto del usuario.

### 4.3 Imagen aceptada (o tercer intento): guardado completo

| Paso | Dónde | Qué ocurre | Trazabilidad |
|------|--------|------------|--------------|
| **4.3.1** | Drive | `upload_image_and_get_link(image_bytes, filename=...)` → `link_imagen`. | **Log:** Si falla: `"Error subiendo a Drive: ..."` o `"Drive: subida fallida o no configurada; link_imagen=NA"`. Si no hay link se usa `"NA"`. |
| **4.3.2** | BD | Se inserta `pagos_whatsapp`: `fecha`, `cedula_cliente`, `imagen` (binario), `link_imagen`. | **BD:** `pagos_whatsapp` INSERT. **Log:** `"Imagen guardada pagos_whatsapp id=... cedula=... link=..."`. |
| **4.3.3** | OCR digitalización | `extract_from_image(image_bytes)` → fecha_deposito, nombre_banco, numero_deposito, cantidad (o "NA"). | **Log:** Si falla: `"Error OCR: ..."`. |
| **4.3.4** | BD | Se inserta `pagos_informe`: cedula, fecha_deposito, nombre_banco, numero_deposito, cantidad, link_imagen, observacion, pagos_whatsapp_id, periodo_envio, fecha_informe. | **BD:** `pagos_informe` INSERT. |
| **4.3.5** | Google Sheets | `append_row(cedula, fecha_dep, nombre_banco, numero_dep, cantidad, link_imagen, periodo, observacion)`. | **Log:** Si falla: `"Sheets: no se escribió la fila..."` o `"Error escribiendo en Sheet: ..."`. |
| **4.3.6** | Reinicio conversación | `intento_foto=0`, `estado=esperando_cedula`, se limpian cedula, nombre_cliente, observacion. | **BD:** `conversacion_cobranza` UPDATE. |
| **4.3.7** | Respuesta | Se envía mensaje de agradecimiento (mensaje IA si fue aceptable; si se aceptó por 3er intento, mensaje fijo de gracias). | **Persistencia:** `mensaje_whatsapp` OUTBOUND con ese texto. |

**Criterio de verificación:**

- **Trazabilidad BD:** Para un reporte completado debe existir: 1 fila en `pagos_whatsapp` (con `cedula_cliente` y `link_imagen`), 1 fila en `pagos_informe` con el mismo `link_imagen` y `pagos_whatsapp_id` apuntando al id de `pagos_whatsapp`.
- **Trazabilidad externa:** En Google Drive debe existir el archivo subido; en la hoja de cálculo configurada debe aparecer una nueva fila con cedula, fecha, banco, etc.
- **Trazabilidad conversación:** Tras guardar, la conversación debe quedar en `estado=esperando_cedula` y sin cédula, de modo que el siguiente mensaje sea tratado como nuevo reporte (bienvenida de nuevo).

---

## 5. Resumen de tablas y logs por tipo de evento

| Evento | Tablas afectadas | Logs relevantes |
|--------|------------------|------------------|
| Cualquier mensaje entrante | `mensaje_whatsapp` (INBOUND) | "Procesando mensaje WhatsApp - ID: ..., From: ..., Type: ..." |
| Cualquier respuesta del bot | `mensaje_whatsapp` (OUTBOUND) | "WhatsApp enviado a ... (cobranza)" si envío OK |
| Nueva conversación | `conversacion_cobranza` INSERT | — |
| Cambio de estado (cédula, confirmación, foto) | `conversacion_cobranza` UPDATE | "Conversación ... reiniciada como nuevo caso" (solo si obsoleto) |
| Imagen no aceptada (reintento) | `conversacion_cobranza` UPDATE (intento_foto) | "Imagen no digitalizada: IA no aceptó, intento X/3 (no_digitaliza=photo_retry); respuesta: ..." |
| Imagen aceptada / 3er intento | `pagos_whatsapp` INSERT, `pagos_informe` INSERT, `conversacion_cobranza` UPDATE | "Digitalizando imagen: cedula=..."; "Imagen guardada pagos_whatsapp id=..."; "Imagen digitalizada: pagos_whatsapp_id=... pagos_informe_id=..."; posibles warnings de Drive/Sheets/OCR |

---

## 6. Checklist rápido de verificación del flujo

1. **Webhook:** Cada mensaje entrante genera un log "Procesando mensaje WhatsApp" y la respuesta del webhook indica 1 mensaje procesado.
2. **Historial:** Cada mensaje (entrante y respuesta) queda en `mensaje_whatsapp`; en Comunicaciones se ve el hilo por teléfono.
3. **Estados:** En `conversacion_cobranza` la secuencia es `esperando_cedula` → `esperando_confirmacion` → `esperando_foto` → (tras guardar) de nuevo `esperando_cedula`.
4. **Protocolo:** Si en `esperando_confirmacion` el usuario envía foto, no se pide cédula; se pide "Primero confirma con Sí o No...".
5. **Inactividad:** Tras 24 h sin mensajes, el siguiente mensaje recibe bienvenida y estado se reinicia.
6. **Papeleta guardada:** Cada foto aceptada (o 3er intento) genera 1 `pagos_whatsapp` + 1 `pagos_informe` con mismo `link_imagen` y `pagos_whatsapp_id`; opcionalmente fila en Google Sheet.
7. **Otra información:** Mensajes con palabras clave de "información/llamar/ayuda" reciben el mensaje con el teléfono 0424-4359435 sin avanzar el flujo de cédula/confirmación/foto.

---

## 7. Por qué una imagen recibida no se digitaliza

La **digitalización** (guardar en Drive, `pagos_whatsapp`, OCR → `pagos_informe`, Sheet) solo ocurre cuando la imagen **se acepta**: bien porque la IA la considera válida (recibo de pago legible) o porque es el **tercer intento** de foto. Si no se cumple ninguna de las dos, la imagen **no se digitaliza** y el usuario recibe un mensaje pidiendo otra foto.

En los logs del backend, cada caso en que **no** se digitaliza queda identificado con `no_digitaliza=<causa>`:

| Causa en log (`no_digitaliza=`) | Significado | Qué revisar |
|---------------------------------|-------------|-------------|
| **need_cedula** | No hay conversación, o estado no es `esperando_foto`, o falta cédula. | El usuario debe seguir el flujo: cédula → confirmar Sí/No → luego enviar foto. Si envió la foto antes de confirmar, el bot pide "Primero confirma con Sí o No...". |
| **primero_confirmar** | Estado = `esperando_confirmacion`. El usuario envió foto sin haber dicho Sí/No. | El usuario debe responder Sí o No a la confirmación y después enviar la foto. |
| **image_skipped** | No hay token de WhatsApp configurado. | Configuración → WhatsApp: Access token. |
| **image_no_url** | Meta no devolvió la URL del media. | Problema puntual con la API de Meta; puede reintentar. |
| **image_error** | Falló la descarga de la imagen (red, timeout, token). | Log completo: "Error descargando imagen: ...". Revisar token y conectividad. |
| **image_empty** | La imagen descargada está vacía. | Raro; revisar que el media en Meta sea válido. |
| **photo_retry** | La IA no aceptó la imagen (no es recibo válido o no se ve bien) y aún no es el 3.er intento. | El usuario debe enviar otra foto más clara o de un recibo de pago válido. Al **tercer intento** se digitaliza igual (y se marca observación si no confirmó identidad). |

**Cómo localizar en logs una imagen que no se digitalizó:**

1. Buscar por el teléfono (parcial, p. ej. `58***`) o por la hora del mensaje.
2. Buscar la línea `"Procesando mensaje WhatsApp"` con `Type: image` o `Type: document`.
3. Justo después, buscar una línea que contenga **`no_digitaliza=`**. Esa causa explica por qué no se guardó en `pagos_whatsapp` / `pagos_informe`.
4. Si aparece **`Digitalizando imagen:`** y luego **`Imagen digitalizada: pagos_whatsapp_id=... pagos_informe_id=...`**, la imagen sí se digitalizó (Drive, BD, OCR, Sheet). Si después hay un warning de Sheets, la fila está en BD pero puede no estar en la hoja.

**Resumen:** La imagen no se digitaliza si el flujo no está en "esperando_foto" con cédula, si falla la descarga, o si la IA no la acepta y es intento 1 o 2. Al tercer intento siempre se digitaliza.

---

## 8. Mismo número se contacta más de una vez al día

Hay **una sola fila por teléfono** en `conversacion_cobranza` (campo `telefono` único). Tras **cada reporte completado** (foto aceptada o 3.er intento), esa misma fila se **reinicia**: `estado=esperando_cedula`, `cedula=None`, `nombre_cliente=None`, etc.

Por tanto:

- **Mismo número, mismo día, después de haber completado un reporte:** El siguiente mensaje recibe de nuevo la **bienvenida** y puede hacer un **segundo reporte** (cédula → confirmación → foto). No hay límite de “un reporte por número por día”: puede reportar varios pagos el mismo día.
- **Mismo número, mismo día, sin haber completado:** Sigue en el mismo flujo (por ejemplo `esperando_foto`); los mensajes se procesan en orden (ej. intentos 1, 2, 3 de foto).
- **Mismo número, tras más de 24 h sin escribir:** Se trata como **nuevo caso** (inactividad): se reinicia la conversación y recibe bienvenida de nuevo.

En BD: cada reporte completado genera **una fila nueva** en `pagos_whatsapp` y `pagos_informe`; el mismo teléfono puede tener varias filas en un mismo día.

Con esto puedes auditar el flujo paso a paso tanto en BD como en logs y en la UI de Comunicaciones.
