# Auditoría integral: notificaciones y correo

## Alcance

- `app/core/email.py` (envío SMTP, encoding, MIME)
- `app/core/email_config_holder.py` (configuración)
- `app/api/v1/endpoints/notificaciones_tabs.py` (flujo de envío por pestaña)
- `app/api/v1/endpoints/notificaciones.py` (plantillas, contexto cobranza)
- `app/api/v1/endpoints/configuracion_email.py` (config y prueba de email)
- `app/services/plantilla_cobranza.py` (render de plantilla COBRANZA)

---

## Errores corregidos en esta auditoría

### 1. **Validación de configuración SMTP antes de enviar** (`email.py`)

- **Riesgo:** Si `get_smtp_config()` devolvía dict sin `smtp_host`/`smtp_user` (o sin contraseña), el código accedía a `cfg["smtp_host"]` y luego fallaba en `server.login()` con un error poco claro.
- **Corrección:** Tras `cfg = get_smtp_config()` se valida:
  - Existencia de `smtp_host` y `smtp_user`.
  - Contraseña presente y no igual a `"***"`.
  - Si falla, se devuelve `(False, "No hay servidor SMTP configurado..."` o `"Falta contrasena SMTP..."`).

### 2. **Normalización UTF-8 de `body_text`** (`email.py`)

- **Riesgo:** Solo se normalizaba `body_html`; si `body_text` llegaba en bytes o con caracteres no UTF-8 (p. ej. desde otra capa o BD), podían producirse errores al construir el MIME o al serializar.
- **Corrección:** Se aplica la misma lógica que a `body_html`: asegurar que sea `str` y que sea encodable en UTF-8 (decodificar desde bytes si aplica, o reemplazar caracteres inválidos).

---

## Estado actual (sin errores críticos pendientes)

| Área | Estado |
|------|--------|
| **Encoding** | `body_text` y `body_html` se normalizan a UTF-8; mensaje se envía como bytes UTF-8 (`msg_bytes`) para evitar `UnicodeEncodeError` en smtplib. |
| **MIME** | Con adjuntos: `multipart/mixed` con primera parte `multipart/alternative` (plain + html). Sin adjuntos: `multipart/alternative`. |
| **Data URL** | Se reemplaza `base64/` por `base64,` en el HTML antes de adjuntar. |
| **Config SMTP** | Se valida `smtp_host`, `smtp_user` y contraseña antes de conectar. |
| **Modo pruebas** | Redirección a `email_pruebas` cuando está activo; excepción con `respetar_destinos_manuales=True` (ej. “Enviar Email de Prueba”). |

---

## Posibles mejoras (no críticas)

### 1. **`email.py`**

- **Subject / From con no ASCII:** El Subject y los headers se asignan como cadenas; con `policy=SMTP` y serialización en UTF-8 ya se evita el fallo en `sendmail`. Opcional: usar `email.utils.formataddr` o codificación RFC 2047 para Subject si algún cliente antiguo falla con UTF-8 en headers.
- **Reutilización de `msg_str`/`msg_bytes`:** Las dos ramas (puerto 465 y 587) repiten la construcción de `msg_str` y `msg_bytes`. Se podría calcular una vez antes del `if port == 465` y usar el mismo valor en ambos `sendmail`.
- **Límite de tamaño de adjuntos:** No hay comprobación de tamaño total de adjuntos; servidores SMTP suelen tener límites (p. ej. 25 MB). Opcional: comprobar tamaño antes de enviar y devolver error claro.

### 2. **`notificaciones_tabs.py`**

- **Item sin `contexto_cobranza` con plantilla COBRANZA:** Si la plantilla es COBRANZA pero `build_contexto_cobranza_para_item` devuelve `None` (p. ej. sin `prestamo_id`), no se asigna `body_html` y se envía solo texto plano. Es coherente con el diseño; opcional: log de advertencia cuando tipo COBRANZA pero sin contexto.
- **Manejo de excepciones por item:** Si un item falla (p. ej. al generar PDF), se registra la excepción y se sigue con el siguiente; el resultado incluye `fallidos`. Correcto; no hay cambio necesario.

### 3. **`notificaciones.py`**

- **`get_plantilla_asunto_cuerpo` sin plantilla:** Cuando no hay `plantilla_id` o la plantilla no está activa, se usa `asunto_default.format(...)` y `cuerpo_default.format(...)`. Los valores del item se obtienen con `item.get(..., or "")` etc., por lo que no debería haber `KeyError`; si algún campo no existe, podría verse "None" en el texto. Opcional: normalizar todos los valores a `str` y sustituir `None` por `""` antes del `format`.
- **Placeholders en modo pruebas:** `_item_placeholder_pruebas()` y `_contexto_cobranza_placeholder()` están bien definidos; el flujo modo pruebas/producción queda claro.

### 4. **`configuracion_email.py`**

- **Probar con cuerpo/asunto personalizados:** El endpoint `/probar` acepta `subject` y `mensaje` (body); si el frontend envía texto con tildes/ñ, la normalización UTF-8 en `send_email` lo cubre.
- **Validación de destino:** Se comprueba que el destino tenga `@` y que el dominio tenga punto y TLD de al menos 2 caracteres; adecuado.

### 5. **Seguridad y buenas prácticas**

- Contraseñas enmascaradas en respuestas API (`***`).
- Uso de `_sanitize_smtp_error` / `_sanitize_imap_error` para no exponer detalles sensibles.
- Encriptación de campos sensibles en BD (email_config_holder); desencriptación al cargar.

---

## Resumen

- **Errores corregidos:** Validación de configuración SMTP antes de usar y normalización UTF-8 de `body_text`.
- **Estado:** No se detectan errores críticos pendientes en el flujo de notificaciones y correo.
- **Mejoras opcionales:** Refactorizar duplicación de `msg_str`/`msg_bytes`, posible límite de tamaño de adjuntos, log cuando COBRANZA sin contexto, y normalización explícita de valores en `format` de asunto/cuerpo por defecto.
