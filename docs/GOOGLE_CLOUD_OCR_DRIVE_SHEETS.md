# Google Cloud: qué necesitas para OCR, Drive y Sheets

## ¿Garantía de conexión perfecta con Sheet, Drive y OCR?

**Sí, siempre que la verificación de la app lo confirme.** La app no “confía” en la config: hace **llamadas reales** a las APIs de Google y te dice si cada una responde bien.

| Servicio | Qué se comprueba |
|----------|------------------|
| **Drive** | Subida de un archivo de prueba en la carpeta configurada y borrado inmediato (misma operación que las papeletas). |
| **Sheets** | Lectura de la hoja y **escritura** de una fila de prueba en una fila alta (luego se borra). Así se garantiza que el informe de pagos podrá escribir. |
| **OCR (Vision)** | Una llamada mínima a `text_detection`. Si responde, Vision API está operativa. |

Si en **Configuración → Informe pagos → Estado de conexiones** los tres muestran **Conectado** y el detalle indica “Conexión correcta…”, entonces **hay conexión correcta** con Drive, Sheets y OCR con la configuración actual. Si alguno falla, el mensaje indica qué revisar (credenciales, ID, compartir con la cuenta).

La conexión depende de tu entorno (credenciales, IDs, carpetas/hojas compartidas). La app no puede garantizarla “desde fuera”; lo que hace es **verificarla con pruebas reales** y mostrarte el resultado.

---

## Revisar la conexión con Google Drive

La app comprueba la conexión con Drive de forma real: sube un archivo de prueba en la carpeta configurada y lo borra. Eso se hace al cargar la pestaña **Informe pagos** y al pulsar **Verificar ahora** en "Estado de conexiones".

### Qué se comprueba

1. **Credenciales:** Cuenta de servicio (JSON) o OAuth (tras "Conectar con Google"). Si faltan o el token OAuth está expirado, verás "Sin credenciales" o "Token OAuth expirado o revocado...".
2. **ID de carpeta:** Debe estar rellenado. Si no, verás "No hay ID de carpeta configurado...".
3. **Acceso a la carpeta:** Se intenta crear un archivo `_test_conexion_pagos.txt` en esa carpeta y luego borrarlo. Si la carpeta no existe o la cuenta no tiene permiso, falla.

### Mensajes típicos y qué hacer

| Mensaje | Causa | Qué hacer |
|--------|--------|-----------|
| **Sin credenciales** | No hay JSON de cuenta de servicio ni OAuth completado. | Pega el JSON en "Credenciales Google" o haz "Conectar con Google" y autoriza. |
| **Token OAuth expirado o revocado** | Usas OAuth y el refresh falló. | Haz clic de nuevo en "Conectar con Google" y vuelve a autorizar. |
| **No hay ID de carpeta configurado** | El campo "ID de carpeta Drive" está vacío. | Copia el ID de la URL de la carpeta (entre `/folders/` y el final) y pégalo en la configuración. |
| **Carpeta no encontrada o sin acceso** | ID incorrecto o la carpeta no está compartida con la cuenta. | Comprueba el ID; comparte la carpeta con el email de la cuenta de servicio (JSON) o con la cuenta que usaste en "Conectar con Google", rol **Editor**. |
| **Sin permiso** | La cuenta no tiene permiso de escritura en la carpeta. | Comparte la carpeta en Drive con rol **Editor** con esa cuenta. |
| **Conexión correcta** | La prueba de subida/borrado funcionó. | No hace falta cambiar nada. |

### Dónde se usa Drive en el flujo

- **WhatsApp:** Cuando el usuario envía una foto de papeleta aceptada, la imagen se sube a esa carpeta y se guarda el enlace en `pagos_whatsapp.link_imagen` y en el informe. Si Drive falla en ese momento, el backend guarda `link_imagen=NA` y registra un warning en logs.

---

## Evaluación de la conexión según documentación Google Cloud

Revisión de cómo la app implementa la conexión frente a la [documentación oficial de Google](https://developers.google.com/drive/api/guides/about-auth) y [Vision API](https://cloud.google.com/vision/docs/authentication).

### Drive API

| Requisito oficial | Implementación en la app | ¿Correcto? |
|-------------------|---------------------------|------------|
| **Scope** recomendado para crear/modificar archivos que la app abre o que el usuario comparte con la app | Uso de `https://www.googleapis.com/auth/drive.file` (scope no sensible, per-file access). | Sí. Coincide con la documentación: *"Create new Drive files, or modify existing files, that you open with an app or that the user shares with an app"*. |
| **Cuenta de servicio** o **OAuth** | Se soportan ambos: JSON de cuenta de servicio o OAuth (client_id, client_secret, refresh_token). | Sí. |
| **Refresh token** en almacenamiento seguro | El refresh_token se guarda en BD (tabla `configuracion`, clave `informe_pagos_config`). Se usa para obtener access_token al vuelo. | Sí. La doc indica *"Save refresh tokens in secure, long-term storage"*. |
| **Carpeta compartida** con la cuenta | Con cuenta de servicio: la carpeta debe estar compartida con el `client_email` del JSON (rol Editor). Con OAuth: la carpeta está en la Drive del usuario que autorizó. | Sí. Los mensajes de verificación lo indican (404/403 y texto de ayuda). |

Conclusión: la conexión con Drive está alineada con la documentación (scope `drive.file`, credenciales SA u OAuth, verificación real con subida/borrado de archivo de prueba).

### Vision API (OCR)

| Requisito oficial | Implementación en la app | ¿Correcto? |
|-------------------|---------------------------|------------|
| **Autenticación** | Se usan las mismas credenciales que para Drive/Sheets: `get_google_credentials(["https://www.googleapis.com/auth/cloud-vision"])` (cuenta de servicio o OAuth). | Sí. Vision acepta credenciales de cuenta de servicio u OAuth con el scope adecuado. |
| **Cliente** | `vision.ImageAnnotatorClient(credentials=creds)` con creds inyectadas (no solo `GOOGLE_APPLICATION_CREDENTIALS`). | Sí. Permite usar la config de la app (JSON u OAuth) sin depender del entorno. |

Conclusión: la conexión con Vision (OCR) es correcta; la verificación de estado hace una llamada mínima a `text_detection` para comprobar que la API responde.

### Posibles mejoras (opcionales)

- **Variable de entorno** `GOOGLE_APPLICATION_CREDENTIALS`: la doc recomienda usarla para desarrollo local con archivo JSON. La app no la usa porque las credenciales vienen de la BD; es coherente para un entorno multi-tenant/configurable.
- **Scope Drive más amplio**: si en el futuro se necesitara acceder a archivos que la app no ha creado ni el usuario ha abierto con la app, habría que valorar `drive` o `drive.readonly` (scopes restringidos y con requisitos de verificación). Con la carpeta compartida con la cuenta de servicio, `drive.file` es suficiente.

En resumen: la conexión con Google Cloud (Drive, Sheets, Vision) está bien planteada según la documentación oficial y la verificación de estado comprueba con llamadas reales que todo funciona.

---

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

## Configuración por caso (página Informe pagos)

En **Configuración → Informe pagos** (`/pagos/configuracion?tab=informe-pagos`) puedes usar **solo una** de las dos formas de credenciales: **cuenta de servicio (JSON)** o **OAuth**. No hace falta rellenar las dos.

---

### Caso 1: Solo cuenta de servicio (JSON)

**Qué llenar en la página:**

| Campo en la página | Qué poner |
|--------------------|-----------|
| **ID carpeta Google Drive** | ID de la carpeta (de la URL `.../folders/ESTE_ID`). Ej: `1ABC...xyz`. |
| **Credenciales Google (cuenta de servicio JSON)** | Todo el contenido del archivo `.json` descargado de Google Cloud (cuenta de servicio → Claves → JSON). Empieza por `{"type":"service_account",...}`. |
| **ID Google Sheet** *(opcional)* | Si quieres informe en Sheets: ID de la hoja (de la URL `.../d/ESTE_ID/edit`). |
| **Destinatarios del informe (emails)** *(opcional)* | Emails separados por coma que reciben el link a las 6:00, 13:00 y 16:30. Ej: `a@ejemplo.com, b@ejemplo.com`. |

**Dejar vacío:** Client ID (OAuth), Client Secret (OAuth). No uses el botón "Conectar con Google".

**Después:** Pulsa **Guardar configuración** y luego **Verificar ahora**. Drive, Sheets y OCR deben pasar a Conectado si la carpeta y la hoja están compartidas con el `client_email` del JSON (rol Editor).

---

### Caso 2: Solo OAuth (sin JSON de cuenta de servicio)

**En Google Cloud Console (antes):**

1. **APIs y servicios → Credenciales → Crear credenciales → ID de cliente de OAuth** (tipo "Aplicación web").
2. En **URIs de redirección autorizados** añade **exactamente** la URL que usa el backend (sin barra final). Si no tienes `BACKEND_PUBLIC_URL` en el servidor, el backend usa por defecto:
   - **`https://pagos-f2qf.onrender.com/api/v1/configuracion/informe-pagos/google/callback`**
   - Si en Render tienes `BACKEND_PUBLIC_URL=https://rapicredit.onrender.com`, entonces usa:  
     `https://rapicredit.onrender.com/api/v1/configuracion/informe-pagos/google/callback`
   - Si Google muestra "redirect_uri_mismatch", la URI que envía la app **no** está en esta lista: entra en tu cliente OAuth → **URIs de redirección autorizados** y añade la URL exacta que aparece en el mensaje de error (o la de arriba según tu backend).
3. Copia el **Client ID** y el **Client secret** del cliente OAuth.

**Qué llenar en la página:**

| Campo en la página | Qué poner |
|--------------------|-----------|
| **ID carpeta Google Drive** | ID de la carpeta donde se guardan las papeletas (de la URL de la carpeta). Esa carpeta debe estar en la **cuenta de Google** con la que vas a hacer "Conectar con Google". |
| **Client ID (OAuth)** | El Client ID del cliente OAuth. Ej: `123456789-xxx.apps.googleusercontent.com`. |
| **Client Secret (OAuth)** | El Client secret del cliente OAuth. |
| **ID Google Sheet** *(opcional)* | ID de la hoja de informe. La hoja debe ser de la **misma cuenta de Google** que autorices. |
| **Destinatarios del informe (emails)** *(opcional)* | Emails separados por coma. |

**Dejar vacío:** No pegues nada en "Credenciales Google (cuenta de servicio JSON)".

**Pasos:**

1. Guarda la configuración (**Guardar configuración**).
2. Pulsa **Conectar con Google (OAuth)**. Se abrirá Google para que autorices con una cuenta de Google (esa cuenta debe ser la dueña de la carpeta y la hoja, o tenerlas compartidas con ella).
3. Tras autorizar, volverás a la página con un mensaje de éxito; el sistema habrá guardado el token OAuth.
4. Pulsa **Verificar ahora**. Drive, Sheets y OCR deben pasar a Conectado.

Si "Verificar ahora" sigue mostrando "Sin credenciales" o "Token OAuth expirado...", comprueba que la **URI de redirección** en Google Cloud coincida exactamente con la del backend (sin barra final, con `/api/v1/configuracion/informe-pagos/google/callback`).

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
