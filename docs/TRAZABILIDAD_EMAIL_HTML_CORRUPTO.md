# Trazabilidad: correo con HTML corrupto

## Flujo completo (origen → envío)

```
[BD] plantillas_notificacion.cuerpo (HTML de la plantilla)
       ↓
[notificaciones_tabs.py] _enviar_correos_items()
  → get_plantilla_asunto_cuerpo(db, plantilla_id, item, ..., modo_pruebas=usar_solo_pruebas)
       ↓
[notificaciones.py] get_plantilla_asunto_cuerpo()
  → plantilla = db.get(PlantillaNotificacion, plantilla_id)
  → cuerpo = render_plantilla_cobranza(plantilla.cuerpo, contexto_cobranza)
  → contexto_cobranza incluye LOGO_URL = "https://.../logos/rapicredit-public.png"
       ↓
[plantilla_cobranza.py] render_plantilla_cobranza(texto, contexto)
  → Sustituye {{LOGO_URL}}, {{CLIENTES.NOMBRE_COMPLETO}}, etc. en el texto
  → Si la plantilla tiene base64 inline (no {{LOGO_URL}}), ese contenido viene tal cual de BD
       ↓
[notificaciones_tabs.py] body_html = cuerpo   (solo si tipo COBRANZA)
  → send_email(to_email, asunto, cuerpo, body_html=body_html, attachments=...)
       ↓
[email.py] send_email()
  → Normalización UTF-8 y data URL (base64/ → base64,)
  → MIMEMultipart: alternative (plain + html) y, con adjuntos, dentro de mixed
  → msg.as_string() → SMTP
```

## Puntos donde puede corromperse el HTML

| Punto | Riesgo | Qué hacer |
|-------|--------|-----------|
| **Plantilla en BD** | Si el cuerpo se guardó con base64 inline y la columna/conexión no es UTF-8, al leer puede salir corrupto. Base64 muy largo puede truncarse o duplicarse al guardar. | Usar en la plantilla `{{LOGO_URL}}` y no pegar imágenes en base64. Asegurar que la BD y el backend usen UTF-8. |
| **Lectura plantilla** | SQLAlchemy devuelve str; si el driver/BD devuelve bytes en otro encoding, el string puede tener caracteres inválidos. | En send_email se normaliza body_html a UTF-8 válido antes de MIMEText. |
| **Data URL** | `data:image/jpeg;base64/...` (barra) es inválido; debe ser `base64,` (coma). Algunos editores guardan mal. | En email.py se reemplaza `base64/` → `base64,` antes de montar el MIME. |
| **MIME** | Con adjuntos, si plain y html van como partes hermanas en mixed, el cliente puede mostrar solo la primera o el código. | Estructura corregida: primer parte = multipart/alternative (plain + html), luego adjuntos. |
| **Charset** | Si body_html tiene bytes no UTF-8, MIMEText(..., "html", "utf-8") o as_string() pueden fallar o generar partes inválidas. | Normalizar body_html a str UTF-8 válido antes de adjuntar. |

## Recomendación para la plantilla

- En el **cuerpo de la plantilla** (pestaña Plantilla cuerpo email / COBRANZA) usar:
  - `<img src="{{LOGO_URL}}" ... />`  
  - y **no** pegar imágenes como `data:image/jpeg;base64,...` (evita corrupción por tamaño/encoding en BD y en el correo).

## Archivos implicados

- `backend/app/api/v1/endpoints/notificaciones_tabs.py` – obtiene cuerpo, asigna body_html, llama send_email.
- `backend/app/api/v1/endpoints/notificaciones.py` – get_plantilla_asunto_cuerpo, build_contexto_cobranza_para_item, LOGO_URL en contexto.
- `backend/app/services/plantilla_cobranza.py` – render_plantilla_cobranza, construir_contexto_cobranza (LOGO_URL).
- `backend/app/core/email.py` – send_email: normalización UTF-8, base64/, estructura MIME.
