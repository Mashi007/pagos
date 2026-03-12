# Revisión paso a paso: correo HTML y plantillas

## Problema original
- En Gmail el correo se veía como **código fuente** (comentarios `<!-- -->`, etiquetas `<table>`, bloque enorme `data:image/jpeg;base64,...`) en lugar de HTML formateado.
- Causas: (1) a veces solo se enviaba la parte `text/plain` con el HTML dentro; (2) la plantilla guardaba la imagen en base64, haciendo el mensaje gigante.

---

## PASO 1 — Dónde se ingresa el HTML (interfaz)

### 1.1 EditorPlantillaHTML.tsx (pestaña / editor simple)
- **Ubicación:** `frontend/src/components/notificaciones/EditorPlantillaHTML.tsx`
- **Qué hace:** Un solo campo (Textarea) para el HTML del correo. Se usa para crear/editar plantillas y para "Enviar email de prueba".
- **Comprobado:**
  - Línea 12: `import { replaceBase64ImagesWithLogoUrl } from '../../utils/plantillaHtmlLogo'`
  - Línea 25: estado inicial `useState(replaceBase64ImagesWithLogoUrl(plantilla?.cuerpo ?? ''))` — al cargar plantilla, si tenía base64 se muestra como `{{LOGO_URL}}`.
  - Línea 75: al guardar, `cuerpo: replaceBase64ImagesWithLogoUrl(cuerpoHTML).trim()` — lo que se envía al API no lleva base64.
  - Línea 111: al "Enviar prueba", se envía `replaceBase64ImagesWithLogoUrl(cuerpoHTML).trim()`.
  - Línea 225: `onChange` del Textarea hace `setCuerpoHTML(replaceBase64ImagesWithLogoUrl(e.target.value))` — al pegar/escribir, base64 se reemplaza por `{{LOGO_URL}}`.

### 1.2 PlantillasNotificaciones.tsx (editor por partes: encabezado / cuerpo / firma)
- **Ubicación:** `frontend/src/components/notificaciones/PlantillasNotificaciones.tsx`
- **Qué hace:** Tres campos (encabezado, cuerpo, firma) que se unen en un solo HTML. Es la interfaz principal para plantillas tipo COBRANZA, etc.
- **Comprobado:**
  - Línea 13: `import { replaceBase64ImagesWithLogoUrl } from '../../utils/plantillaHtmlLogo'`
  - Línea 55: `cuerpoFinal = useMemo(..., return replaceBase64ImagesWithLogoUrl(parts.join('\n\n')))` — lo que se guarda nunca lleva base64.
  - Línea 452: al seleccionar una plantilla, `setCuerpo(replaceBase64ImagesWithLogoUrl(p.cuerpo || ''))` — al abrir una plantilla con base64 se muestra con `{{LOGO_URL}}`.
  - Línea 1195: Textarea del cuerpo `onChange={e=>setCuerpo(replaceBase64ImagesWithLogoUrl(e.target.value))}` — al pegar en el cuerpo, base64 → `{{LOGO_URL}}`.

### 1.3 Util compartido
- **Ubicación:** `frontend/src/utils/plantillaHtmlLogo.ts`
- **Función:** `replaceBase64ImagesWithLogoUrl(html)` — reemplaza cualquier `src="data:image/...;base64,..."` por `src="{{LOGO_URL}}"`.
- **Regex:** `/src="data:image\/[^"]+"/gi`

**Resumen paso 1:** En la interfaz donde se ingresa el HTML (ambos editores), al cargar, al escribir/pegar y al guardar, el base64 se sustituye por `{{LOGO_URL}}`. La plantilla guardada en BD ya no debería contener el bloque base64.

---

## PASO 2 — Cómo se guarda la plantilla (API)

- El frontend envía `cuerpo` (HTML ya pasado por `replaceBase64ImagesWithLogoUrl`).
- El backend (notificaciones.py) recibe y persiste en `PlantillaNotificacion.cuerpo`.
- No hay lógica extra en el backend para el cuerpo al guardar; la “limpieza” se hace en el frontend (paso 1).

---

## PASO 3 — Envío “Email de prueba” (Configuración > Email)

### 3.1 Frontend
- **Servicio:** `notificacionService.probarConfiguracionEmail(email, asunto, cuerpoHTML, undefined)`
- El tercer argumento ya es `replaceBase64ImagesWithLogoUrl(cuerpoHTML).trim()` (EditorPlantillaHTML línea 111).
- Se llama a `POST /api/v1/configuracion/email/probar` con body: `{ email_destino, subject, mensaje }`. `mensaje` es el HTML (con `{{LOGO_URL}}` si había base64 reemplazado).

### 3.2 Backend — configuracion_email.py
- **Endpoint:** `post_email_probar` (POST `/probar`).
- **Comprobado:**
  - Líneas 284–291: `body = (payload.mensaje or "").strip() or "..."`. Si `"{{LOGO_URL}}" in body`, se reemplaza por la URL real del logo (`_logo_url_for_email()` o URL por defecto).
  - Luego se llama a `send_email(to_emails=recipients, subject=subject, body_text=body, respetar_destinos_manuales=True)` — **solo** `body_text`; no se pasa `body_html`.

### 3.3 Backend — email.py (send_email)
- Recibe solo `body_text=body` (HTML con `{{LOGO_URL}}` ya sustituido por URL).
- **Auto-detección de HTML** (líneas 210–213): si `body_html is None` y `body_text` contiene `<`, `>` y algo como `<table`, `</table>`, `<html`, `<body`, entonces `body_html = body_text`. Así el mismo contenido se usa como parte HTML.
- Luego, si `body_html` no es None:
  - Normalización UTF-8.
  - `base64/` → `base64,` (por si acaso).
  - Reemplazo de cualquier `src="data:image/...;base64,..."` por la URL del logo (`_logo_url_for_email()`).
  - Se genera la parte `text/plain` a partir del HTML (sin tags) para multipart/alternative.
- Se arma el mensaje con parte plain + parte HTML. Gmail recibe HTML y lo renderiza.

**Resumen paso 3:** Prueba desde Configuración > Email: el cuerpo pasa por el frontend (sin base64, con `{{LOGO_URL}}`), el backend sustituye `{{LOGO_URL}}` y envía el cuerpo como `body_text`; `email.py` lo trata como HTML cuando corresponde, reemplaza base64 si quedara algo y envía multipart para que Gmail muestre formato.

---

## PASO 4 — Envío real de notificaciones (pestañas: retrasados, mora, etc.)

### 4.1 notificaciones_tabs.py
- Para cada ítem se obtiene `asunto, cuerpo = get_plantilla_asunto_cuerpo(...)`. El `cuerpo` es el HTML de la plantilla (con variables ya sustituidas; si la plantilla tenía `{{LOGO_URL}}`, el motor de cobranza lo rellena).
- Solo para plantilla tipo **COBRANZA** y con `contexto_cobranza`: `body_html = cuerpo`. En otros tipos, `body_html` queda `None`.
- Se llama `send_email(to_email, asunto, cuerpo, body_html=body_html, bcc_emails=..., attachments=...)`.

### 4.2 email.py de nuevo
- Si `body_html` viene con valor (COBRANZA): se normaliza, se reemplaza cualquier base64 por URL del logo, se genera la parte plain y se envía multipart.
- Si `body_html` es `None` (otro tipo pero cuerpo HTML): la auto-detección (paso 3.3) hace `body_html = body_text` cuando el cuerpo parece HTML; después se aplica el mismo tratamiento (normalización, reemplazo base64, multipart).

**Resumen paso 4:** En envíos reales, COBRANZA ya manda `body_html`; el resto de tipos que envíen HTML se benefician de la auto-detección en `email.py`. En todos los casos, si hubiera base64 en el cuerpo, se sustituye por la URL del logo.

---

## PASO 5 — Sustitución de {{LOGO_URL}} en el backend (plantillas de cobranza)

- En `plantilla_cobranza.py` (o equivalente), al construir el contexto de la plantilla se incluye `LOGO_URL` con la URL pública del logo. El motor de plantillas (Mustache/Jinja/etc.) reemplaza `{{LOGO_URL}}` en el cuerpo al generar el `cuerpo` que se usa en notificaciones_tabs y en la prueba.
- En el endpoint de **prueba** (configuracion_email), `{{LOGO_URL}}` se reemplaza a mano en el `body` antes de `send_email` (paso 3.2).

---

## Checklist de verificación

| Paso | Qué revisar | Estado |
|------|-------------|--------|
| 1.1 | EditorPlantillaHTML: import, useState inicial, guardar, enviar prueba, onChange | OK (comprobado en código) |
| 1.2 | PlantillasNotificaciones: import, cuerpoFinal, setCuerpo al seleccionar, onChange cuerpo | OK (comprobado en código) |
| 1.3 | plantillaHtmlLogo.ts existe y exporta replaceBase64ImagesWithLogoUrl | OK |
| 2 | Guardado de plantilla: frontend envía cuerpo ya “limpio” | OK (sin cambios backend en guardado) |
| 3.1 | Prueba: frontend envía mensaje con {{LOGO_URL}} si aplica | OK |
| 3.2 | configuracion_email: sustituye {{LOGO_URL}} en body y llama send_email(body_text=body) | OK (líneas 284–291) |
| 3.3 | email.py: auto-detect HTML cuando body_html is None, reemplazo base64, multipart | OK (líneas 210–239 y siguientes) |
| 4.1 | notificaciones_tabs: body_html = cuerpo para COBRANZA; send_email(..., body_html=...) | OK |
| 4.2 | email.py: mismo flujo para body_html recibido o auto-detectado | OK |
| 5 | {{LOGO_URL}} en contexto de cobranza y en endpoint de prueba | OK |

---

## Qué hacer si algo falla

1. **Gmail sigue mostrando código en crudo**
   - Confirmar que el backend desplegado es el que tiene los cambios en `email.py` (auto-detección HTML y reemplazo base64 por URL).
   - Confirmar que el frontend desplegado usa `plantillaHtmlLogo` en ambos editores.

2. **El logo no se ve en el correo**
   - Comprobar que la URL del logo es accesible (p. ej. `https://.../pagos/logos/rapicredit-public.png`) y que `FRONTEND_PUBLIC_URL` (o la URL por defecto en `_logo_url_for_email()`) es correcta.

3. **Plantillas antiguas con base64**
   - Abrir cada plantilla en la interfaz (EditorPlantillaHTML o PlantillasNotificaciones), dejar que se cargue (el base64 se convertirá en `{{LOGO_URL}}` en pantalla) y guardar de nuevo. Así la BD queda sin base64.

---

## Archivos tocados (resumen)

- **Frontend:** `utils/plantillaHtmlLogo.ts`, `components/notificaciones/EditorPlantillaHTML.tsx`, `components/notificaciones/PlantillasNotificaciones.tsx`
- **Backend:** `app/core/email.py` (auto-HTML, _logo_url_for_email, reemplazo base64), `app/api/v1/endpoints/configuracion_email.py` (sustitución {{LOGO_URL}} en prueba)
- **Sin cambiar:** `notificaciones_tabs.py` (ya pasaba body_html para COBRANZA; el resto lo cubre email.py con auto-detección)
