# Google Cloud: qué necesitas para OCR, Drive y Sheets

## Configurar Google Drive para el proyecto (paso a paso)

Usa **el mismo proyecto** donde tienes el cliente OAuth "Cobranzas" (ej. `cobranzas-485720`). No hace falta crear otro proyecto.

### 1. Activar la API de Drive

1. [Google Cloud Console](https://console.cloud.google.com/) → selecciona tu proyecto.
2. **APIs y servicios** → **Biblioteca**.
3. Busca **Google Drive API** → **Habilitar**.
4. (Opcional, para informe) Busca **Google Sheets API** → **Habilitar**.
5. (Opcional, para OCR) Busca **Cloud Vision API** → **Habilitar**.

### 2. Crear cuenta de servicio (para Drive/Sheets/Vision)

1. **APIs y servicios** → **Credenciales**.
2. **+ Crear credenciales** → **Cuenta de servicio** (no "ID de cliente de OAuth").
3. Nombre: p. ej. `rapicredit-drive-informe`.
4. **Crear y continuar** (roles opcionales) → **Listo**.
5. En la lista, haz clic en la cuenta de servicio recién creada.
6. Pestaña **Claves** → **Añadir clave** → **Crear clave nueva** → **JSON** → **Crear**.
7. Se descarga un archivo `.json`. **Guárdalo en lugar seguro**; es el que usarás en la app.

### 3. Carpeta en Google Drive

1. En [Google Drive](https://drive.google.com) crea una carpeta (ej. "Papeletas RapiCredit").
2. Abre la carpeta → la URL será algo como:  
   `https://drive.google.com/drive/folders/1ABC...xyz`
3. El **ID de la carpeta** es la parte `1ABC...xyz` (entre `/folders/` y el final).
4. **Compartir** la carpeta → añade el **email de la cuenta de servicio** (aparece en el JSON como `client_email`, tipo `rapicredit-drive-informe@cobranzas-485720.iam.gserviceaccount.com`) con rol **Editor**.

### 4. Configuración en la app

1. Entra en la app → **Configuración** → pestaña **Informe pagos** (Drive, Sheets, OCR).
2. **Credenciales Google (JSON):** abre el archivo JSON descargado, copia **todo** el contenido y pégalo aquí.
3. **ID de carpeta Drive:** pega el ID de la carpeta (ej. `1ABC...xyz`).
4. Si usas informe en Sheets: crea o abre la hoja, compártela con el mismo email de la cuenta de servicio como **Editor**, y pega el ID de la hoja (de la URL `https://docs.google.com/spreadsheets/d/ID/edit`) en **ID de hoja Sheets**.
5. Guarda los cambios.

A partir de ahí, cuando el bot reciba una foto de papeleta (tras cédula y confirmación), la subirá a esa carpeta y guardará el link; si tienes Sheets configurado, se escribirá también en el informe.

---

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
| **Client ID (OAuth)** / **Client Secret (OAuth)** | Si usas OAuth: ID y secreto del cliente OAuth (ej. "Cobranzas"). Luego **Conectar con Google (OAuth)**. |
| **Credenciales Google (JSON)** | Si usas cuenta de servicio: contenido completo del archivo JSON. |
| **ID de carpeta Drive** | ID de la carpeta (solo el ID, ej. `1PwYB4-e2-Uh69gCj0sIa9_tI2b4qUHl4`), no la URL completa. |
| **ID de hoja Sheets** | ID de la hoja (solo el ID, entre `/d/` y `/edit` en la URL), no la URL completa. |
| **Destinatarios del informe** | Emails que reciben el enlace a la hoja (6:00, 13:00, 16:30). Opcional. |

Esa configuración se persiste en la base de datos (tabla `configuracion`, clave `informe_pagos_config`). El backend lee de ahí para:

- **OCR / claridad:** `ocr_service.py` usa Vision con credenciales (cuenta de servicio u OAuth). Si no hay credenciales, la claridad no se comprueba y la imagen se trata como “no clara” hasta el 3.º intento.
- **Drive:** `google_drive_service.py` sube la imagen con las mismas credenciales y `google_drive_folder_id`.
- **Sheets:** `google_sheets_informe_service.py` escribe en la hoja con las mismas credenciales y `google_sheets_id`.

---

## OAuth (alternativa a cuenta de servicio)

Si tu organización no permite crear claves de cuenta de servicio, puedes usar **OAuth** con un cliente OAuth de Google Cloud (ej. "Cobranzas"):

1. En **Configuración → Informe pagos**, rellena **Client ID (OAuth)** y **Client Secret (OAuth)**.
2. En Google Cloud Console → **Credenciales** → tu cliente OAuth → **URIs de redirección autorizados**, añade **solo** la URL completa del callback del backend (no la del frontend). Ejemplo para este proyecto:  
   `https://pagos-f2qf.onrender.com/api/v1/configuracion/informe-pagos/google/callback`  
   En **Orígenes autorizados de JavaScript** puedes tener: `https://rapicredit.onrender.com`.
3. Guarda la configuración y pulsa **Conectar con Google (OAuth)**. Autoriza con la cuenta de Google que tendrá acceso a Drive, Sheets y Vision.
4. Tras conectar, **Drive, Sheets y OCR (Vision)** usan esa misma cuenta OAuth; no hace falta el JSON de cuenta de servicio.

Los scopes que se solicitan al autorizar son: Drive (archivos), Sheets y Cloud Vision (OCR).

---

## Ejemplo de configuración (este proyecto)

| Dónde | Valor |
|------|--------|
| **Backend (callback OAuth)** | `https://pagos-f2qf.onrender.com/api/v1/configuracion/informe-pagos/google/callback` |
| **Frontend (origen JS)** | `https://rapicredit.onrender.com` |
| **Carpeta Drive** | ID: `1PwYB4-e2-Uh69gCj0sIa9_tI2b4qUHl4` — en la app se pega solo el ID, no la URL. |
| **Hoja Sheets** | ID: `1YkUw8v3XEUM07vIkHiqvxFIKfq4-BHN_JtDcvR4rCRU` (ej. hoja «Papeletas_WhatsApp») — en la app se pega solo el ID. |

Carpeta y hoja deben estar **compartidas** con la cuenta de Google que uses al pulsar **Conectar con Google (OAuth)** (rol Editor). **OCR** no requiere configuración aparte: usa la misma cuenta OAuth (Vision API ya incluida en los scopes).

---

## Resumen

| Pregunta | Respuesta |
|----------|-----------|
| ¿A qué cuentas de Google está conectado? | **OAuth:** la cuenta con la que haces "Conectar con Google". **Cuenta de servicio:** el JSON; no hay login con Gmail. |
| ¿Qué necesito de Google Cloud? | Proyecto, **Vision API**, **Drive API** y **Sheets API** activadas. **OAuth:** cliente OAuth (Client ID + Secret) y URI de redirección. **Cuenta de servicio:** clave JSON. |
| ¿El OCR usa la misma cuenta? | Sí. **OCR (Vision)** usa la misma cuenta OAuth o el mismo JSON que Drive y Sheets. |
| ¿Dónde configuro? | En la app: **Configuración → Informe pagos** (OAuth: Client ID, Secret, Conectar con Google; o JSON; ID carpeta Drive; ID hoja Sheets). |
