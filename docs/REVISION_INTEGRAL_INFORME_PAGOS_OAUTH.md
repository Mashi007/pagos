# Revisión integral: Informe de pagos, OAuth, Drive, Sheets, OCR y bot WhatsApp

**Fecha:** 2026-02-02  
**Alcance:** Flujo OAuth Google, configuración informe pagos (Drive/Sheets/OCR), mensajes bot WhatsApp, documentación y seguridad.

---

## 1. Resumen ejecutivo

| Área | Estado | Notas |
|------|--------|--------|
| Backend OAuth (authorize + callback) | OK | Scopes Drive, Sheets, Vision; state en BD; redirect a frontend con ?google_oauth=ok/error |
| Credenciales Google (helper) | OK | OAuth o cuenta de servicio según `use_google_oauth()` |
| Drive / Sheets / OCR | OK | Usan `get_google_credentials(scopes)` correctamente |
| Frontend Informe pagos | OK | Client ID/Secret, Conectar con Google, detección ?google_oauth=ok/error |
| Seguridad (enmascarar secretos) | Corregido | PUT configuración ahora enmascara client_secret y refresh_token en la respuesta |
| Documentación | OK | GOOGLE_CLOUD_OCR_DRIVE_SHEETS.md actualizado con OAuth y ejemplo de IDs |
| Mensajes WhatsApp | OK | Incluye "Gracias. (Cédula {cedula} reportada.)" tras foto aceptada |

---

## 2. Backend

### 2.1 OAuth (configuracion_informe_pagos.py)

- **GET /configuracion/informe-pagos/google/authorize:** Requiere auth, genera `state`, lo guarda en BD, redirige a Google con scopes Drive, Sheets, Cloud Vision. OK.
- **GET /configuracion/informe-pagos/google/callback:** Público (sin auth). Valida `state`, intercambia `code` por tokens, guarda `refresh_token` en `informe_pagos_config`, redirige a frontend `rapicredit.onrender.com/pagos/configuracion?tab=informe-pagos&google_oauth=ok|error`. OK.
- **Scopes:** `drive.file`, `spreadsheets`, `cloud-vision`. OK.
- **Redirect URI backend:** `{BACKEND_PUBLIC_URL}/api/v1/configuracion/informe-pagos/google/callback`. Fallback `https://pagos-f2qf.onrender.com`. OK.
- **GET /configuracion:** Enmascara `google_credentials_json`, `google_oauth_client_secret`, `google_oauth_refresh_token` (***). OK.
- **PUT /configuracion:** Tras guardar, la respuesta `configuracion` ahora también enmascara `google_oauth_client_secret` y `google_oauth_refresh_token` (corregido en esta revisión).

### 2.2 Router (api/v1/__init__.py)

- Callback OAuth registrado con prefijo `/configuracion/informe-pagos` (público). OK.
- Router con auth registrado en `configuracion.router` con prefijo `/informe-pagos`. OK.

### 2.3 google_credentials.py

- `get_google_credentials(scopes)`: si `use_google_oauth()` usa refresh_token + client_id/secret; si no, cuenta de servicio. OK.
- Manejo de excepciones y logging. OK.

### 2.4 Drive (google_drive_service.py)

- Usa `get_google_credentials(DRIVE_SCOPE)`, `get_google_drive_folder_id()`. Sube imagen, crea permiso "anyone reader", devuelve link. OK.

### 2.5 Sheets (google_sheets_informe_service.py)

- `_get_sheets_service()` usa `get_google_credentials(SHEETS_SCOPE)`. append_row, ensure_sheet_tab con pestañas 6am, 1pm, 4h30. OK.

### 2.6 OCR (ocr_service.py)

- `_get_vision_client()` con `get_google_credentials(VISION_SCOPE)`. imagen_suficientemente_clara (≥50 caracteres), extract_from_image. OK.

### 2.7 WhatsApp (whatsapp_service.py)

- Mensajes: bienvenida, cédula, confirmación, foto (20 cm), foto poco clara (intento n/3), **MENSAJE_RECIBIDO = "Gracias. (Cédula {cedula} reportada.)"**. OK.
- Flujo: cédula → confirmación → imagen (claridad, 3 intentos) → Drive + OCR + Sheet + pagos_whatsapp + pagos_informe. OK.
- Si la subida a Drive falla: se registra **WARNING** "Drive: subida fallida o no configurada; link_imagen=NA. Revisa OAuth conectado, ID carpeta y que la carpeta esté compartida con la cuenta OAuth." y se continúa con link_imagen="NA".

---

## 3. Frontend

### 3.1 InformePagosConfig.tsx

- Campos: Client ID, Client Secret (OAuth), ID carpeta Drive, ID hoja Sheets, destinatarios, credenciales JSON (cuenta de servicio). OK.
- Botón "Conectar con Google (OAuth)": redirige a `getBackendBaseUrl() + '/api/v1/configuracion/informe-pagos/google/authorize'`. OK.
- useEffect detecta `?google_oauth=ok|error`, muestra toast y limpia query. OK.
- Estado "OAuth conectado" cuando `google_oauth_refresh_token` está presente. OK.
- Icono: `Link` (lucide-react), no `Link2`, para evitar error de build. OK.

---

## 4. Configuración y documentación

### 4.1 GOOGLE_CLOUD_OCR_DRIVE_SHEETS.md

- APIs: Drive, Sheets, Vision. OK.
- Opción OAuth: Client ID/Secret, URI de redirección, Conectar con Google. OK.
- Ejemplo de configuración: backend callback, frontend, ID carpeta `1PwYB4-e2-Uh69gCj0sIa9_tI2b4qUHl4`, ID hoja `1YkUw8v3XEUM07vIkHiqvxFIKfq4-BHN_JtDcvR4rCRU`. OK.

### 4.2 IDs y URLs

- Carpeta Drive: `1PwYB4-e2-Uh69gCj0sIa9_tI2b4qUHl4` (t**I** mayúscula, no "tl"). OK.
- Hoja Sheets: `1YkUw8v3XEUM07vIkHiqvxFIKfq4-BHN_JtDcvR4rCRU`. OK.
- Callback OAuth: `https://pagos-f2qf.onrender.com/api/v1/configuracion/informe-pagos/google/callback`. OK.

---

## 5. Corrección aplicada en esta revisión

- **PUT /configuracion informe pagos:** La respuesta `configuracion` no enmascaraba `google_oauth_client_secret` ni `google_oauth_refresh_token`. Corregido: ambos se devuelven como `"***"` en la respuesta, igual que en GET.

---

## 6. Si la imagen no aparece en Drive

1. **OAuth conectado:** En Configuración → Informe pagos debe verse "OAuth conectado". Si no, guardar Client ID y Secret y pulsar "Conectar con Google (OAuth)".
2. **Carpeta compartida:** La carpeta con ID configurado debe estar **compartida con la cuenta de Google** usada en OAuth, rol **Editor**.
3. **ID correcto:** Usar exactamente `1PwYB4-e2-Uh69gCj0sIa9_tI2b4qUHl4` (con **I** mayúscula en `tI2b4q`).
4. **Logs backend:** Buscar "Google Drive no configurado", "Drive: subida fallida o no configurada" o "Error subiendo imagen a Google Drive" al enviar una papeleta.

---

## 6.1 Si no aparece la fila en Google Sheets

1. **OAuth conectado:** Igual que Drive; debe verse "OAuth conectado" en Informe pagos.
2. **Hoja compartida:** La hoja **Papeletas_WhatsApp** (ID `1YkUw8v3XEUM07vIkHiqvxFIKfq4-BHN_JtDcvR4rCRU`) debe estar **compartida con la misma cuenta de Google** usada en OAuth, rol **Editor**.
3. **ID hoja en la app:** En Configuración → Informe pagos, **ID Google Sheet** = `1YkUw8v3XEUM07vIkHiqvxFIKfq4-BHN_JtDcvR4rCRU` (solo el ID, sin URL). Guardar.
4. **Logs backend:** Buscar "Google Sheets no configurado", "Sheets: no se escribió la fila" o "Error escribiendo en Google Sheets" al enviar una papeleta.

---

## 7. Recomendaciones

1. **Variables de entorno:** Asegurar `BACKEND_PUBLIC_URL` en producción (ej. `https://pagos-f2qf.onrender.com`) para que el redirect_uri sea correcto.
2. **Redirect post-OAuth:** Las URLs `redirect_ok` y `redirect_fail` están fijas a `https://rapicredit.onrender.com/pagos/configuracion?...`. Si el frontend cambia de dominio, habría que hacerlas configurables (ej. desde `settings` o BD).
3. **Limpieza de state OAuth:** Los registros `google_oauth_state_{state}` se borran tras usar o al expirar (10 min). Opcional: job periódico que borre states antiguos por si alguno queda huérfano.
4. **Pruebas:** Tras desplegar, verificar: Conectar con Google → Drive y Sheets compartidos con esa cuenta → envío de papeleta por WhatsApp → aparición de archivo en Drive y fila en Sheets.

---

## 8. Checklist de despliegue

- [ ] BACKEND_PUBLIC_URL configurado en Render (backend).
- [ ] En Google Cloud: URI de redirección = `https://pagos-f2qf.onrender.com/api/v1/configuracion/informe-pagos/google/callback`.
- [ ] App: Client ID, Client Secret, ID carpeta Drive, ID hoja Sheets guardados.
- [ ] Carpeta Drive y hoja Sheets compartidas con la cuenta OAuth (Editor).
- [ ] "Conectar con Google (OAuth)" ejecutado y mensaje "OAuth conectado" visible.
- [ ] Prueba de envío de papeleta por WhatsApp y comprobación en Drive y Sheets.
