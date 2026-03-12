# Generación de email desde HTML – mensaje no corrupto al cargarse

Este documento confirma cómo se genera el correo desde las plantillas HTML y qué garantías hay para que **al cargarse el mensaje en el cliente (Gmail, etc.) no se vea corrupto** (sin HTML crudo ni imágenes base64 enormes).

## Flujo de generación

1. **Plantillas** (Configuración → Plantillas): el cuerpo se guarda en BD como HTML (asunto + cuerpo con variables `{{nombre}}`, `{{LOGO_URL}}`, etc.).
2. **Envío** (Notificaciones por pestaña o “Enviar con plantilla”): se obtiene asunto y cuerpo con variables sustituidas (`get_plantilla_asunto_cuerpo` o `_sustituir_variables`). Para tipo COBRANZA se usa `render_plantilla_cobranza` y se inyecta `LOGO_URL` en el contexto.
3. **`send_email`** (backend `app/core/email.py`): recibe el cuerpo (y opcionalmente `body_html`). Si solo se pasa cuerpo HTML en el primer argumento, se detecta y se usa también como `body_html`. Antes de montar el MIME se aplica **`_sanitize_html_for_email`**.

## Garantías en backend (evitar mensaje corrupto)

En `app/core/email.py`, **`_sanitize_html_for_email(body_html, logo_url)`** se aplica siempre al HTML que se envía. Hace lo siguiente:

1. **Typo base64:** corrige `base64/` → `base64,` para que las data URLs se interpreten bien.
2. **Variable sin sustituir:** reemplaza `{{LOGO_URL}}` por la URL real del logo (por si no se sustituyó en la plantilla).
3. **Imágenes inline base64 largas:** sustituye `src="data:image/..."` o `src='data:image/...'` (solo si la data URL tiene ≥ 300 caracteres) por `src="<logo_url>"`. Así:
   - No se envía un payload enorme que rompe o ralentiza el cliente.
   - Iconos SVG pequeños (p. ej. WhatsApp) se conservan.
   - El correo se renderiza correctamente en Gmail y evita ver “código + base64” como contenido.

Además:

- **Parte texto:** si el cuerpo es HTML, se genera una versión `text/plain` sin tags ni data URLs (`_strip_html_to_plain`) para clientes que no muestran HTML.
- **MIME:** el correo se envía como `multipart/alternative` con `text/plain` y `text/html; charset=utf-8`, para que los clientes muestren el HTML cuando lo soporten.

## Frontend (editor de plantillas)

En el frontend, al guardar o pegar HTML se usa **`replaceBase64ImagesWithLogoUrl`** (`frontend/src/utils/plantillaHtmlLogo.ts`): reemplaza data URLs de imagen largas (≥ 400 caracteres) por `{{LOGO_URL}}`. Así la plantilla guardada en BD ya no contiene base64 enorme; el backend sigue aplicando `_sanitize_html_for_email` por si alguna plantilla antigua o otra fuente aún trae base64 o `{{LOGO_URL}}` sin sustituir.

## Resumen

- **Generación:** el mensaje se genera desde el HTML de la plantilla (variables sustituidas) y luego se sanitiza en `send_email`.
- **Al cargarse el mensaje:** el cliente recibe HTML sin base64 largo y con `{{LOGO_URL}}` ya reemplazado por la URL del logo, y un `text/plain` limpio, por lo que no debe mostrarse “corrupto” (HTML crudo o bloques base64 visibles). Si en el pasado se vio base64 en el correo, era por plantillas guardadas antes de estos reemplazos; los envíos nuevos quedan cubiertos por `_sanitize_html_for_email`.
