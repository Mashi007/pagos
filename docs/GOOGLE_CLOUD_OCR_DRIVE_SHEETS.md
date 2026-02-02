# Requisitos de Google Cloud para OCR, Drive y Sheets (Informe pagos)

Para que el flujo de cobranza (imágenes de papeletas → OCR → Drive → Google Sheets) funcione, necesitas **un solo proyecto de Google Cloud** y **una cuenta de servicio** que use estas APIs.

---

## 1. Qué usa la aplicación

| Función | API de Google | Uso |
|--------|----------------|-----|
| **OCR** (extraer texto de la imagen) | **Cloud Vision API** | Text Detection sobre la foto de la papeleta |
| **Guardar imagen y obtener link** | **Google Drive API** (v3) | Subir archivo a una carpeta y generar link “cualquiera con el enlace puede ver” |
| **Digitalizar en hoja** | **Google Sheets API** (v4) | Añadir filas en una hoja (pestañas 6am, 1pm, 4h30) |

Las tres usan **las mismas credenciales**: una **cuenta de servicio** (archivo JSON).

---

## 2. Pasos en Google Cloud Console

### 2.1 Proyecto

1. Entra en [Google Cloud Console](https://console.cloud.google.com/).
2. Crea un proyecto nuevo o elige uno existente (por ejemplo “RapiCredit” o “Informe-pagos”).

### 2.2 Activar APIs

En **APIs y servicios → Biblioteca** activa:

| API | Nombre en consola | Para qué |
|-----|-------------------|----------|
| **Cloud Vision API** | “Cloud Vision API” | OCR (text_detection) |
| **Google Drive API** | “Google Drive API” | Subir imágenes y obtener link |
| **Google Sheets API** | “Google Sheets API” | Escribir filas en la hoja del informe |

- Busca cada una por nombre y pulsa **Activar**.

### 2.3 Cuenta de servicio

1. **APIs y servicios → Credenciales**.
2. **+ Crear credenciales → Cuenta de servicio**.
3. Nombre (ej. `informe-pagos-app`), ID se genera solo.
4. **Crear y continuar** (rol opcional; se puede dejar sin rol y dar acceso por “compartir” en Drive/Sheets).
5. **Listo** (no hace falta añadir usuarios).
6. En la tabla de cuentas de servicio, abre la que creaste → pestaña **Claves**.
7. **Añadir clave → Crear clave nueva → JSON** → Descargar.
8. Guarda ese JSON en un lugar seguro; **no lo subas a repositorios públicos**.  
   Ese JSON es el que pegarás (o cargarás) en **Configuración > Informe pagos → Credenciales Google (cuenta de servicio JSON)**.

Anota el **email de la cuenta de servicio** (ej. `informe-pagos-app@tu-proyecto.iam.gserviceaccount.com`). Lo usarás para compartir la carpeta de Drive y la hoja de Sheets.

---

## 3. Google Drive: carpeta para las imágenes

1. En [Google Drive](https://drive.google.com/) crea una **carpeta** (ej. “Papeletas RapiCredit”).
2. Abre la carpeta y mira la URL. El **ID de la carpeta** es la parte entre `folders/` y el siguiente `?` o el final:
   - URL: `https://drive.google.com/drive/folders/1ABC...xyz`
   - **ID de carpeta:** `1ABC...xyz`
3. **Compartir** la carpeta:
   - Clic derecho en la carpeta → **Compartir**.
   - Añade el **email de la cuenta de servicio** (el del JSON).
   - Rol: **Editor** (para que la app pueda crear archivos y enlaces “cualquiera con el enlace”).
   - Guardar.

Ese **ID de carpeta** es el que configuras en **Configuración > Informe pagos → ID carpeta Google Drive**.

---

## 4. Google Sheets: hoja del informe

1. Crea una **hoja de cálculo** en [Google Sheets](https://sheets.google.com/) (nombre ej. “Informe pagos RapiCredit”).
2. El **ID de la hoja** está en la URL:
   - URL: `https://docs.google.com/spreadsheets/d/1XYZ...abc/edit`
   - **ID de hoja:** `1XYZ...abc`
3. **Compartir** la hoja:
   - **Compartir** (arriba a la derecha).
   - Añade el **mismo email de la cuenta de servicio**.
   - Rol: **Editor**.
   - Guardar.

Ese **ID de hoja** es el que configuras en **Configuración > Informe pagos → ID Google Sheet**.  
La app crea sola las pestañas **6am**, **1pm** y **4h30** si no existen.

---

## 5. Resumen: qué configurar en la app

En **Configuración > Informe pagos (Drive, Sheets, OCR)** necesitas:

| Campo en la app | Origen |
|-----------------|--------|
| **ID carpeta Google Drive** | ID de la carpeta de Drive (URL: `.../folders/ESTE_ID`). Carpeta compartida con el email de la cuenta de servicio como Editor. |
| **Credenciales Google (cuenta de servicio JSON)** | Contenido completo del archivo JSON descargado en “Cuenta de servicio → Claves → JSON”. |
| **ID Google Sheet** | ID de la hoja de cálculo (URL: `.../d/ESTE_ID/...`). Hoja compartida con el email de la cuenta de servicio como Editor. |
| **Destinatarios del informe (emails)** | Emails que recibirán el link a la hoja (6:00, 13:00, 16:30). |

---

## 6. Checklist rápido

- [ ] Proyecto en Google Cloud creado o elegido.
- [ ] **Cloud Vision API** activada.
- [ ] **Google Drive API** activada.
- [ ] **Google Sheets API** activada.
- [ ] Cuenta de servicio creada y **clave JSON** descargada.
- [ ] Carpeta en Drive creada, **compartida con el email de la cuenta de servicio (Editor)** y **ID de carpeta** copiado.
- [ ] Hoja de Sheets creada, **compartida con el email de la cuenta de servicio (Editor)** y **ID de hoja** copiado.
- [ ] En la app: **Configuración > Informe pagos** rellenado con ID carpeta, JSON de credenciales, ID hoja y destinatarios.

---

## 7. Enlaces útiles

- [Google Cloud Console](https://console.cloud.google.com/)
- [Activar Cloud Vision API](https://console.cloud.google.com/apis/library/vision.googleapis.com)
- [Activar Google Drive API](https://console.cloud.google.com/apis/library/drive.googleapis.com)
- [Activar Google Sheets API](https://console.cloud.google.com/apis/library/sheets.googleapis.com)
- [Crear cuenta de servicio (doc oficial)](https://cloud.google.com/iam/docs/create-service-account)

Con esto tienes todo lo que requiere Google Cloud para configurar OCR (Vision), Drive y Sheets en esta aplicación.
