# Flujo de configuración de email (guardado y comprobación)

## Fuente de verdad

- **Única fuente de verdad:** la tabla `configuracion` (clave `email_config`). Todo lo que se muestra en GET y lo que se usa para enviar/probar viene de ahí (o de .env si no hay nada guardado).

## Operaciones (sin solapamiento)

| Operación | Orden | Qué hace |
|-----------|--------|----------|
| **GET /configuracion** | 1) Cargar desde BD → 2) Rellenar stub desde .env si vacío → 3) Devolver stub con contraseñas enmascaradas (`***`) | Solo lectura. No persiste nada. |
| **PUT /configuracion** | 1) Cargar desde BD → 2) Fusionar payload en stub (no sobrescribir contraseñas si vienen `***` o vacío) → 3) **Validar** (formato email, puertos, obligatorios) → 4) Persistir stub en BD → 5) Actualizar holder en memoria | Guardado. No ejecuta prueba SMTP/IMAP. |
| **POST /probar** (SMTP) | 1) Cargar desde BD → 2) Usar config guardada para enviar un correo de prueba | La prueba usa **siempre** la config ya persistida. Para probar con datos nuevos hay que guardar antes. |
| **POST /probar-imap** | Si el body trae `imap_host`, `imap_user` e `imap_password` (y no `***`), usar esos; si no, cargar desde BD y usar stub | Permite probar IMAP con datos del formulario sin guardar. |

## Legitimación (validación antes de guardar)

En **PUT** se valida antes de persistir:

- **Formato de email:** `smtp_user`, `from_email`, `email_pruebas`, `imap_user` y cada email en `tickets_notify_emails` (regex básico `usuario@dominio.tld`).
- **Puertos:** para Gmail, SMTP solo 587 o 465; IMAP solo 993 o 143. Para otros hosts, puerto entre 1 y 65535.
- **Obligatorios:** servidor SMTP, usuario SMTP, remitente; en modo Pruebas, email de pruebas obligatorio.

Si la validación falla, se responde **400** con el listado de errores y **no se persiste** la configuración.

## Contraseñas

- Si el frontend envía `***` o vacío en `smtp_password` o `imap_password`, el backend **no actualiza** ese campo (se mantiene el valor ya guardado).
- Para cambiar la contraseña hay que **escribirla de nuevo** en el formulario y guardar.
- Las contraseñas se encriptan en BD cuando está definido `ENCRYPTION_KEY`; si no, se guardan en claro (y se cargan correctamente gracias al fallback en `sync_from_db`).

## Archivos relevantes

- **Endpoints:** `backend/app/api/v1/endpoints/configuracion_email.py`
- **Validación:** `backend/app/api/v1/endpoints/email_config_validacion.py`
- **Holder y persistencia:** `backend/app/core/email_config_holder.py`
- **Envío y prueba IMAP:** `backend/app/core/email.py`
