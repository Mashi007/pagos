# Google Cloud: qué necesitas para OCR, Drive y Sheets

## Confirmación: ¿a qué cuentas está conectado?

**No está conectado a cuentas personales de Google** (no hay login con tu Gmail).  
La aplicación usa **una sola cuenta de servicio de Google Cloud** (Service Account). Esa cuenta es la que hace:

- **OCR y claridad de imagen** → Google Cloud **Vision API**
- **Subir papeletas** → Google **Drive API**
- **Escribir el informe** → Google **Sheets API**

Todo con el **mismo JSON de la cuenta de servicio**.

---

## Qué necesitas en Google Cloud

### 1. Proyecto en Google Cloud

1. Entra en [Google Cloud Console](https://console.cloud.google.com/).
2. Crea un proyecto (o usa uno existente).

### 2. Activar las APIs

En **APIs y servicios → Biblioteca**, activa:

| API | Uso en la app |
|-----|----------------|
| **Cloud Vision API** | OCR de papeletas y comprobación de claridad de imagen (≥50 caracteres) |
| **Google Drive API** | Subir la foto de la papeleta y obtener el link |
| **Google Sheets API** | Añadir filas al informe de pagos |

### 3. Cuenta de servicio y JSON

1. **APIs y servicios → Credenciales → Crear credenciales → Cuenta de servicio**.
2. Ponle un nombre (ej. `rapicredit-informe-pagos`) y crea.
3. En la cuenta de servicio, pestaña **Claves** → **Añadir clave → Crear clave nueva → JSON** → descarga el archivo.
4. Ese JSON es el que se configura en la app como **Credenciales Google (JSON)**.

### 4. Permisos en Drive y Sheets

- **Drive:** Crea una carpeta donde quieras guardar las papeletas. Comparte la carpeta con el **email de la cuenta de servicio** (ej. `nombre@proyecto.iam.gserviceaccount.com`) como **Editor**. El ID de esa carpeta (de la URL) es el **ID de carpeta Drive** que configuras en la app.
- **Sheets:** Crea o usa una hoja de cálculo para el informe. Comparte la hoja con el mismo email de la cuenta de servicio como **Editor**. El **ID de la hoja** es el que aparece en la URL:  
  `https://docs.google.com/spreadsheets/d/ESTE_ES_EL_ID/edit`

---

## Dónde se configura en la app

Todo se guarda en **Configuración → Informe pagos** (tab/pestaña de informe de pagos):

| Campo en la app | Descripción |
|-----------------|-------------|
| **Credenciales Google (JSON)** | Contenido completo del archivo JSON descargado de la cuenta de servicio. |
| **ID de carpeta Drive** | ID de la carpeta de Drive donde se suben las imágenes. |
| **ID de hoja Sheets** | ID de la hoja de cálculo del informe. |

Esa configuración se persiste en la base de datos (tabla `configuracion`, clave `informe_pagos_config`). El backend lee de ahí para:

- **OCR / claridad:** `ocr_service.py` usa Vision con `google_credentials_json`. Si no hay credenciales, la claridad no se comprueba y la imagen se trata como “no clara” hasta el 3.º intento.
- **Drive:** `google_drive_service.py` sube la imagen con las mismas credenciales y `google_drive_folder_id`.
- **Sheets:** `google_sheets_informe_service.py` escribe en la hoja con las mismas credenciales y `google_sheets_id`.

---

## Resumen

| Pregunta | Respuesta |
|----------|-----------|
| ¿A qué cuentas de Google está conectado? | A **ninguna cuenta personal**. Solo a **una cuenta de servicio** (Service Account) de Google Cloud. |
| ¿Qué necesito de Google Cloud? | Proyecto, **Vision API**, **Drive API** y **Sheets API** activadas, una **cuenta de servicio** y su **clave JSON**. |
| ¿El OCR usa la misma cuenta? | Sí. **OCR (Vision)** usa el mismo JSON que Drive y Sheets. |
| ¿Dónde pongo el JSON y los IDs? | En la app: **Configuración → Informe pagos** (Credenciales Google, ID carpeta Drive, ID hoja Sheets). |
