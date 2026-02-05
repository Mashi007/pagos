# Flujo de conversación del bot WhatsApp (cobranza / reporte de pago)

Bot de Rapicredit para recibir cédula y foto de papeleta de depósito, digitalizar con OCR y registrar en Drive, BD y Google Sheets.

---

## Estados de la conversación

| Estado | Descripción |
|--------|-------------|
| `esperando_cedula` | El usuario debe enviar su cédula (E/J/V + 6-11 dígitos). |
| `esperando_confirmacion` | El usuario debe confirmar con Sí/No que el pago es a su nombre. |
| `esperando_foto` | El usuario debe enviar la foto de la papeleta de depósito. |
| `esperando_confirmacion_datos` | Tras procesar la imagen, el usuario confirma o corrige los datos leídos (cédula, cantidad, Nº documento). |

---

## Flujo por mensajes

### 1. Entrada (usuario nuevo o inactivo > 5 min)

- **Condición:** No hay conversación para ese teléfono, o la conversación lleva más de **5 minutos** sin actividad.
- **Bot:** Mensaje de bienvenida y petición de cédula.
- **Texto:** *"Hola, bienvenido al servicio de cobranza de Rapicredit. Primero ingresa tu número de cédula sin guiones intermedios (formato: debe empezar por una de las 3 letras E, J o V, seguido de entre 6 y 11 números; puede ser mayúsculas o minúsculas)."*
- **Estado siguiente:** `esperando_cedula`.

Si el usuario escribe algo que parece una consulta general (información, hablar con alguien, etc.), el bot responde: *"Para otras consultas te atendemos por teléfono. Llama al 0424-4359435 y un asistente te atenderá."*

---

### 2. Usuario envía TEXTO en `esperando_cedula`

| Acción usuario | Respuesta del bot | Estado siguiente |
|----------------|-------------------|-------------------|
| Cédula **válida** (E/J/V + 6-11 dígitos) | *"Confirma que el siguiente reporte de pago se realizará a cargo de {nombre}. ¿Sí o No?"* (o *"...a cargo del titular de la cédula {cedula}. ¿Sí o No?"* si no hay nombre en BD) | `esperando_confirmacion` |
| Cédula **inválida** | Mismo mensaje de bienvenida (instrucción de cédula) | `esperando_cedula` |
| Pide otra información | *"Para otras consultas te atendemos por teléfono. Llama al 0424-4359435..."* | sin cambio |

---

### 3. Usuario envía TEXTO en `esperando_confirmacion`

| Acción usuario | Respuesta del bot | Estado siguiente |
|----------------|-------------------|-------------------|
| **Sí** (sí, si, confirmo, correcto, ok, etc.) | *"No se te pedirá otra; te pedimos que vuelvas a tomar una fotografía más clara o que cargues el original. Gracias. Ahora adjunta una foto clara de tu papeleta de depósito o recibo de pago válido, a unos 20 cm. Si no es un recibo válido o no se ve bien se te pedirá otra."* | `esperando_foto` |
| **No** | *"Por favor escribe de nuevo tu número de cédula (E, J o V seguido de 6 a 11 números)."* | `esperando_cedula` (se borra cédula/nombre) |
| Otra cosa / no Sí ni No | *"Por favor responde Sí o No: ¿El reporte de pago es a cargo de {nombre}?"* (reintentos hasta 3) | `esperando_confirmacion` |
| Tras **3 intentos** sin Sí ni No | *"Continuamos. Envía una foto clara de tu papeleta de depósito (recibo de pago válido) a 20 cm."* | `esperando_foto` (se marca observación "No confirma identidad") |

---

### 4. Usuario envía TEXTO en `esperando_foto`

- **Bot:** Recuerda que envíe la foto.
- **Texto:** *"Por favor adjunta una foto clara de tu papeleta de depósito o recibo de pago válido, a 20 cm."* (con nombre si existe: *"{nombre}, ..."*).
- **Estado:** sigue `esperando_foto`.

---

### 5. Usuario envía IMAGEN en `esperando_foto`

- Se descarga la imagen desde Meta, se ejecuta **OCR** (Vision) y se decide si la imagen es "aceptable" (datos útiles o marcación HUMANO).
- **Intentos de foto:** 1, 2 o 3. En el **tercer intento** siempre se acepta (aunque no sea clara).

| Resultado | Respuesta del bot | Qué pasa |
|-----------|-------------------|----------|
| **Imagen aceptable** (OCR extrajo datos o HUMANO) | Mensaje con los datos leídos (cédula, cantidad, Nº documento) y *"Responde *SÍ* para confirmar o escribe las correcciones..."* | Se sube a Drive, se guarda en `pagos_whatsapp` y `pagos_informes`, se escribe fila en Google Sheet. Estado → `esperando_confirmacion_datos`. |
| **Imagen no aceptable, intento 1 o 2** | *"No se te pedirá otra; te pedimos que vuelvas a tomar una fotografía más clara o que cargues el original. Intento 1/3 (o 2/3). Gracias. Ahora adjunta una foto clara..."* | Estado sigue `esperando_foto`, intento_foto += 1. |
| **Imagen no aceptable, intento 3** | Mismo flujo que "aceptable": se digitaliza y se pide confirmación de datos. Si la imagen no era clara, además se **crea ticket automático** y se envía copia al correo configurado (ej. itmaster@rapicreditca.com). | Drive + BD + Sheet + opcional ticket + email. Estado → `esperando_confirmacion_datos`. |
| **Error** (descarga, token, etc.) | *"No pudimos procesar tu imagen en este momento. Por favor intenta enviar otra foto clara de tu papeleta a 20 cm, o llama al 0424-4359435..."* | Sin cambio de estado. Si ya era intento 3, se responde con mensaje de "registrado, te contactaremos si no está clara". |

---

### 6. Usuario envía IMAGEN en otros estados

| Estado actual | Respuesta del bot |
|---------------|-------------------|
| Sin conversación / `esperando_cedula` | Mensaje de bienvenida (pedir cédula). |
| `esperando_confirmacion` | *"Primero confirma con Sí o No que el reporte de pago es a tu nombre. Después envía la foto de tu papeleta de depósito."* |
| `esperando_confirmacion_datos` | *"Responde *SÍ* para confirmar (cédula, cantidad y Nº documento) o escribe las correcciones por texto (ej: Cantidad 100.50, Nº documento 12345)."* |

---

### 7. Usuario envía TEXTO en `esperando_confirmacion_datos`

| Acción usuario | Respuesta del bot | Qué pasa |
|----------------|-------------------|----------|
| **SÍ** (confirmación) | *"Gracias. Datos confirmados y registrados. Si necesitas algo más, llama al 0424-4359435."* | Se marca el informe como CONCILIADO, se actualiza la fila en Sheet. Estado → `esperando_cedula` (listo para nuevo reporte). |
| **Correcciones** (ej. "Cantidad 100.50", "Nº documento 12345") | *"Gracias. Hemos actualizado los datos con tus correcciones. Quedó registrado."* | Se actualizan cédula, cantidad y/o numero_documento en BD y Sheet (estado REVISAR). Estado → `esperando_cedula`. |
| Texto que no es SÍ ni corrección parseable | *"Responde *SÍ* para confirmar o escribe las correcciones (ej: Cantidad 100.50, Nº documento 12345)."* | Sigue `esperando_confirmacion_datos`. |

---

### 8. Usuario envía DOCUMENTO (archivo)

- Si el archivo es **imagen** (jpg, png, etc.): se trata como imagen (mismo flujo que punto 5).
- Si **no** es imagen (p. ej. PDF): *"Por favor envía una foto (imagen) de tu papeleta de depósito, no un documento (PDF u otro archivo)."*

---

### 9. Otros tipos de mensaje

- **Solo texto e imágenes** son procesados para el reporte de pago. Cualquier otro tipo recibe: *"Solo puedo procesar texto e imágenes. Para reportar tu pago envía una foto clara de tu papeleta de depósito."*

---

## Resumen del flujo (diagrama de estados)

```
                    +------------------+
                    |  Usuario escribe |
                    |  o envía imagen  |
                    +--------+---------+
                             |
         +-------------------+-------------------+
         |                   |                   |
         v                   v                   v
  [esperando_cedula]  [esperando_confirmacion]  [esperando_foto]  [esperando_confirmacion_datos]
         |                   |                   |                   |
         | Cédula válida      | Sí                | Imagen OK/3.º      | SÍ → CONCILIADO
         | → confirmación     | → pide foto       | → Drive+BD+Sheet  | Edición → REVISAR
         |                   | No → pide cédula  | → pide confirmar  | → esperando_cedula
         |                   | 3 intentos → foto | datos             |
         +-------------------+-------------------+
```

---

## Archivos de código

- **Flujo y mensajes:** `backend/app/services/whatsapp_service.py`
- **OCR:** `backend/app/services/ocr_service.py`
- **Drive/Sheet:** `backend/app/services/google_drive_service.py`, `backend/app/services/google_sheets_informe_service.py`
- **Ticket automático (recibo no claro 3 intentos):** en `whatsapp_service.py`, función `_crear_ticket_recibo_no_claro` y llamada cuando `aceptado_por_tercer_intento`.

---

## Tiempo de inactividad

Si no hay actividad durante **5 minutos** (`MINUTOS_INACTIVIDAD_NUEVO_CASO`), la conversación se reinicia: se pide de nuevo cédula y luego foto, como si fuera un nuevo reporte.
