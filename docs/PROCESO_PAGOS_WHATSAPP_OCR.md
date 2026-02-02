# Proceso: Imágenes WhatsApp → OCR → Tabla pagos → Google Sheets → Email

## Especificación definida

### 1. Proceso y columnas (OCR + BD + Sheets)

| Columna 1 | Columna 2 | Columna 3 | Columna 4 |
|-----------|-----------|-----------|-----------|
| **Cédula** | **Banco / Entidad Financiera** | **Fecha de depósito** | **Cantidad depositada** |

- OCR (Google Cloud) extrae estos 4 campos del documento de pago (imagen guardada en `pagos_whatsapp`).
- Se guardan en tabla BD **`pagos_informes`** (o `pagos_registrados`) con las mismas columnas.
- Se vuelcan a **Google Sheets** con una pestaña por envío.

### 2. Google Sheets: una pestaña por envío

- **Pestaña 8am** – Pagos del periodo (ej. 5pm día anterior → 8am).
- **Pestaña 2pm** – Pagos del periodo 8am → 2pm.
- **Pestaña 5pm** – Pagos del periodo 2pm → 5pm.

El correo lleva **enlace a la Google Sheet** (y opcionalmente export de esa pestaña).

### 3. Contenido del correo (texto genérico)

Ejemplo:

- **Asunto:** Informe de pagos – 1 de febrero de 2026 – 8 AM  
- **Cuerpo:** Texto genérico tipo: *"Envío informe de pagos del 1 de febrero de 2026 - 8 AM. Ver detalle en la hoja: [LINK GOOGLE SHEET]"*  
- **Adjunto:** Enlace a la Google Sheet (pestaña del periodo).

### 4. Tabla en BD (pagos del informe)

Columnas:

1. **Cédula**
2. **Banco / Entidad Financiera**
3. **Fecha de depósito**
4. **Cantidad depositada**

Más campos de control: id, pagos_whatsapp_id, periodo_envio (8am/2pm/5pm), fecha_informe, created_at.

### 5. Zona horaria

- **Venezuela:** America/Caracas (8:00, 14:00, 17:00 en esa zona).

### 6. Si no hay pagos en el periodo

- **Sí:** se envía correo indicando “Sin pagos en este periodo” y se mantiene el flujo.
- **Después:** los datos se bajan a BD (tabla de pagos); es decir, todo lo extraído por OCR y agrupado por periodo queda guardado en la tabla de pagos en BD.

---

## Flujo técnico resumido

1. WhatsApp recibe imagen → guardar en `pagos_whatsapp` (fecha, cedula_cliente, imagen).
2. Tras guardar → OCR (Google Cloud) sobre la imagen → extraer: Cédula, Banco/Entidad, Fecha depósito, Cantidad depositada.
3. Guardar en tabla BD **pagos_informes** (cedula, banco_entidad_financiera, fecha_deposito, cantidad_depositada, periodo_envio, pagos_whatsapp_id, etc.).
4. Escribir/actualizar **Google Sheets**: una pestaña por periodo (8am, 2pm, 5pm) con esas columnas.
5. **Cron 8:00, 14:00, 17:00** (America/Caracas):  
   - Generar texto genérico del informe (ej. “Informe de pagos del [fecha] - 8 AM”).  
   - Enviar correo con ese texto + enlace a la Google Sheet (pestaña del periodo).  
   - Si no hay pagos: enviar correo “Sin pagos en este periodo”.
6. Toda la configuración (Google Cloud, Sheets, SMTP, destinatarios, horarios) en el **módulo Configuración**.

---

## Configuración en el módulo Configuración

| Variable / Sección | Uso |
|--------------------|-----|
| **Configuración > Informe pagos** | Google Drive folder ID, credenciales Google (JSON service account para Drive + Sheets + Vision), Google Sheet ID, destinatarios del informe. |
| **Google Drive** | Carpeta donde se suben las imágenes; se genera link público por imagen. |
| **Google Sheets** | ID de la hoja; pestañas "6am", "1pm", "4h30" (creadas automáticamente si no existen). |
| **OCR** | Mismas credenciales Google (Vision API habilitada en el proyecto). |
| **Email (SMTP)** | Configuración > Email; se usa para los 3 correos diarios (6:00, 13:00, 16:30). |
| **Destinatarios informe pagos** | Lista de emails (separados por coma) que reciben el link a la hoja. |
| **Horarios envío** | 6:00, 13:00, 16:30 (America/Caracas). |
| **Comunicaciones** | Página Comunicaciones enlaza a Config AI, WhatsApp, Email e Informe pagos para verificar integración. |
