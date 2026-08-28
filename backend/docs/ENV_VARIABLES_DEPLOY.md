# Variables de entorno para despliegue

Referencia de todas las variables usadas por la aplicación (según `app/core/config.py` y uso en endpoints/servicios).

**Mantener `.env.example` actualizado:** copiar o añadir las variables de esta lista que falten en `.env.example` del backend para que el despliegue tenga una plantilla completa.

## Obligatorias

| Variable | Descripción |
|----------|-------------|
| `DATABASE_URL` | URL PostgreSQL (ej. `postgresql://user:pass@host:5432/db`) |
| `SECRET_KEY` | Clave JWT (mín. 32 caracteres, aleatoria) |

Tras cada despliegue que incluya cambios en modelos SQLAlchemy, ejecute migraciones en el mismo entorno que usa `DATABASE_URL`, por ejemplo: `cd backend && alembic upgrade head`. Si en logs aparece `column "gmail_message_id" of relation "gmail_temporal" does not exist`, la base está por debajo de la revisión **064** (`064_pagos_gmail_trazabilidad_ids_evento`); aplicar migraciones corrige el error.

## Base de datos (pool SQLAlchemy, opcional)

Cada worker de Gunicorn tiene su propio pool. Si muchas peticiones lentas en paralelo agotan conexiones (`QueuePool limit ... overflow ... reached`), subir estos valores sin superar `max_connections` de Postgres (aprox. `workers × (DATABASE_POOL_SIZE + DATABASE_MAX_OVERFLOW)`).

| Variable | Default | Descripción |
|----------|---------|-------------|
| `DATABASE_POOL_SIZE` | 10 | Conexiones persistentes por worker |
| `DATABASE_MAX_OVERFLOW` | 20 | Conexiones extra bajo pico |
| `DATABASE_POOL_TIMEOUT` | 60 | Segundos esperando conexión libre |

## General

| Variable | Default | Descripción |
|----------|---------|-------------|
| `DEBUG` | False | Modo depuración |
| `PROJECT_NAME` | Sistema de Pagos | Nombre de la app |
| `VERSION` | 1.0.0 | Versión |
| `API_V1_STR` | /api/v1 | Prefijo API |
| `ENVIRONMENT` | - | production / development (opcional) |

## Seguridad / JWT

| Variable | Default | Descripción |
|----------|---------|-------------|
| `ALGORITHM` | HS256 | Algoritmo JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 240 | Minutos del access token |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 7 | Días del refresh token |
| `REMEMBER_ME_ACCESS_TOKEN_EXPIRE_DAYS` | 30 | Access token con "Recordarme" |
| `REMEMBER_ME_REFRESH_TOKEN_EXPIRE_DAYS` | 90 | Refresh con "Recordarme" |

## Auth

| Variable | Descripción |
|----------|-------------|
| `ADMIN_EMAIL` | Email admin (login sin tabla users) |
| `ADMIN_PASSWORD` | Contraseña admin |
| `RESET_PASSWORD_SECRET` | Secreto header X-Admin-Secret (restablecer password) |
| `MIGRATION_AUDITORIA_SECRET` | Secreto migración FK auditoría (una vez) |
| `FORGOT_PASSWORD_NOTIFY_EMAIL` | Destino del correo "olvidé contraseña" |

## Encriptación

| Variable | Descripción |
|----------|-------------|
| `ENCRYPTION_KEY` | Clave Fernet para valores sensibles en BD (opcional) |

## WhatsApp / Meta

| Variable | Default | Descripción |
|----------|---------|-------------|
| `WHATSAPP_SEND_ENABLED` | **false** | Si **false** (defecto), no se llama a la API de Meta (envío masivo, prueba, bot saliente, descarga de media en flujo cobranza, test «conexión»). Correo y resto del sistema sin cambios. Poner **true** solo si usan Cloud API con credenciales válidas. |
| `WHATSAPP_VERIFY_TOKEN` | — | Token verificación webhook |
| `WHATSAPP_ACCESS_TOKEN` | — | Access Token Meta |
| `WHATSAPP_PHONE_NUMBER_ID` | — | Phone Number ID |
| `WHATSAPP_BUSINESS_ACCOUNT_ID` | — | Business Account ID |
| `WHATSAPP_APP_SECRET` | — | App Secret (verificar firma webhooks) |
| `WHATSAPP_GRAPH_URL` | graph…v18.0 | URL base API Meta |
| `ALERT_WEBHOOK_URL` | — | URL alertas (ej. Slack) cuando falla webhook |
| `SUPPORT_PHONE` | 0424-… | Teléfono soporte (estado ERROR_MAX_INTENTOS) |
| `MESSAGE_DELAY_SECONDS` | 2 | Segundos entre mensajes del bot |

## Email / SMTP

| Variable | Descripción |
|----------|-------------|
| `SMTP_HOST` | Host SMTP |
| `SMTP_PORT` | Puerto (ej. 587) |
| `SMTP_USER` | Usuario SMTP |
| `SMTP_PASSWORD` | Contraseña / app password |
| `SMTP_FROM_EMAIL` | Remitente |
| `TICKETS_NOTIFY_EMAIL` | Emails notificación tickets (coma) |
| `FRONTEND_PUBLIC_URL` | URL frontend (enlaces/logo en emails) |
| `LOGO_PDF_COBRANZA_PATH` | Ruta PNG logo para PDF carta cobranza |
| `ADJUNTO_FIJO_COBRANZA_BASE_DIR` | Directorio base PDFs fijos cobranza |

## AI / OpenRouter

| Variable | Descripción |
|----------|-------------|
| `OPENROUTER_API_KEY` | API Key OpenRouter (nunca en frontend) |
| `OPENROUTER_MODEL` | Modelo por defecto (ej. openai/gpt-4o-mini) |

## Google / Gmail / Gemini

| Variable | Descripción |
|----------|-------------|
| `BACKEND_PUBLIC_URL` | URL pública backend (OAuth redirect) |
| `GOOGLE_CLIENT_ID` | OAuth Client ID |
| `GOOGLE_CLIENT_SECRET` | OAuth Client Secret |
| `AUDITORIA_EMAIL_GOOGLE_CLIENT_ID` | Client ID Web cobranzas (…bitt…) para cobranza@; opcional si Informe de pagos (BD) ya lo tiene |
| `AUDITORIA_EMAIL_GOOGLE_CLIENT_SECRET` | Opcional: si difiere de Informe de pagos (BD), se ignora cuando el Client ID coincide (Opción A) |
| `GMAIL_TOKENS_PATH_COBRANZA` | Ruta JSON tokens OAuth cobranza@ (ej. `/var/data/gmail_tokens_cobranza.json`) |
| `GMAIL_MAILBOX` | Buzón objetivo Auditoría Email (default `cobranza@rapicreditca.com`) |
| `GOOGLE_REDIRECT_URI` | Redirect URI tras autorizar Gmail |
| `GMAIL_TOKENS_PATH` | Ruta JSON tokens Gmail |
| `GEMINI_API_KEY` | API Key Gemini |
| `GEMINI_MODEL` | Modelo Gemini (ej. gemini-2.5-flash) |
| `DRIVE_ROOT_FOLDER_ID` | ID carpeta raíz Drive |
| `PAGOS_GMAIL_SCHEDULED_SCAN_ENABLED` | `true`/`false`: si `ENABLE_AUTOMATIC_SCHEDULED_JOBS=true`, escaneo America/Caracas **lun-vie cada hora 06:00-22:00; sáb-dom cada hora 07:00-19:00**, solo inbox+media **sin etiqueta de usuario** (`has:nouserlabels`). Default en código: `true`. |
| `ENABLE_AUTOMATIC_SCHEDULED_JOBS` | `true`/`false`: activa APScheduler en el proceso líder. **Requerido** para crons (Gmail, Recibos, gestores, ESTADO_CUENTA, D-2 antes, etc.). |
| `ENABLE_CRON_NOTIFICACIONES_2_DIAS_ANTES (eliminado del producto; ignorado)` | `true`/`false`: envío automático pestaña **3 días antes** / d-2-antes (`PAGO_2_DIAS_ANTES_PENDIENTE`). Default `true`. Horario: `CRON_2_DIAS_ANTES_HOURS` + `CRON_2_DIAS_ANTES_MINUTE` Caracas (defecto **07:15 y 18:15**), lun–dom. Idempotente **por slot** HH:MM. |
| `CRON_2_DIAS_ANTES_HOURS` | Horas Caracas separadas por coma (default `7,18`). **Usar esta.** |
| `CRON_2_DIAS_ANTES_HOUR` | Compat: hora única si `HOURS` vacío (default `7`). Si por error se pone `7,18` aquí, se interpreta como `HOURS` y no tumba el arranque. |
| `CRON_2_DIAS_ANTES_MINUTE` | Minuto Caracas compartido (default `15`). |
| `ENABLE_CRON_NOTIFICACIONES_PREJUDICIAL` | `true`/`false`: envío automático **a-2-cuotas** (`PREJUDICIAL`). Default `true`. Horario: `CRON_PREJUDICIAL_HOUR`:`CRON_PREJUDICIAL_MINUTE` Caracas (defecto **00:20**), lun–dom. Idempotente 1 vez/día. |
| `CRON_PREJUDICIAL_HOUR` | Hora Caracas (default `0`). |
| `CRON_PREJUDICIAL_MINUTE` | Minuto Caracas (default `20`). |
| `ENABLE_CRON_NOTIFICACIONES_ATRASO_10_DIAS` | `true`/`false`: envío automático **atraso-10-dias** (`PAGO_10_DIAS_ATRASADO`). Default `true`. Horario: `CRON_ATRASO_10_DIAS_HOUR`:`CRON_ATRASO_10_DIAS_MINUTE` Caracas (defecto **13:15**), lun–dom. Idempotente 1 vez/día. |
| `CRON_ATRASO_10_DIAS_HOUR` | Hora Caracas (default `13`). |
| `CRON_ATRASO_10_DIAS_MINUTE` | Minuto Caracas (default `15`). |
| `ENABLE_CRON_NOTIFICACIONES_DIA_SIGUIENTE (eliminado del producto; ignorado)` | `true`/`false`: envío automático **día siguiente al vencimiento** (`PAGO_1_DIA_ATRASADO`, ruta `/notificaciones`). Default `true`. Horario: `CRON_DIA_SIGUIENTE_HOURS` + `CRON_DIA_SIGUIENTE_MINUTE` Caracas (defecto **09:15 y 17:15**), lun–dom. Idempotente **por slot** HH:MM (mañana y tarde independientes). |
| `CRON_DIA_SIGUIENTE_HOURS` | Horas Caracas separadas por coma (default `9,17`). |
| `CRON_DIA_SIGUIENTE_MINUTE` | Minuto Caracas compartido (default `15`). |
| `ENABLE_CRON_NOTIFICACIONES_ESTADO_CUENTA` | `true`/`false`: envío masivo ESTADO_CUENTA (PDF) diario. Default `true`. Horario: `CRON_ESTADO_CUENTA_HOUR`:`CRON_ESTADO_CUENTA_MINUTE` Caracas (defecto **09:00**) con catch-up horario hasta `CRON_ESTADO_CUENTA_CATCHUP_HOUR_END` (defecto **11**). Tope 600/día. |
| `CRON_ESTADO_CUENTA_HOUR` | Hora Caracas del primer disparo (default `9`). |
| `CRON_ESTADO_CUENTA_MINUTE` | Minuto Caracas (default `0`). |
| `CRON_ESTADO_CUENTA_CATCHUP_HOUR_END` | Última hora inclusive de reintento (default `11`). |
| `ENABLE_BCV_WIDGET_TASA_JOB` | `true`/`false`: bot GET al recuadro USD de `bcv.org.ve` **lun-vie Caracas 08:30, 16:00, 16:30, 17:00, 17:30, 18:00, 18:30**; guarda `tasa_bcv` con la fecha valor (siguiente hábil). Si esa fecha ya tiene BCV, no consulta de nuevo. Si el WAF bloquea, no reintenta en bucle. Default: `true`. |
| `BCV_WIDGET_URL` | URL del recuadro (default `https://www.bcv.org.ve/`) |
| `PAGOS_GMAIL_DELAY_BETWEEN_GEMINI_SECONDS` | Delay entre llamadas Gemini |
| `PAGOS_GMAIL_MAX_EMAILS_PER_RUN` | Máx correos por ejecución (0 = sin límite) |
| `PAGOS_GMAIL_DOWNLOAD_EXCEL_MAX_ITEMS` | Máx filas Excel sin fecha |
| `PAGOS_GMAIL_MIN_IMAGE_BYTES` | Mín bytes para imagen comprobante |

## Reportes / Tasa

| Variable | Descripción |
|----------|-------------|
| `TASA_USD_BS_DEFAULT` | Tasa USD/Bs por defecto (opcional) |
| `EXCHANGERATE_API_URL` | URL API tasa (default exchangerate-api.com) |

## Otros

| Variable | Descripción |
|----------|-------------|
| `REDIS_URL` | URL Redis (opcional) |
| `SENTRY_DSN` | DSN Sentry (opcional) |
| `CORS_ORIGINS` | Orígenes CORS (JSON array o coma) |
| `LOGO_UPLOAD_DIR` | Directorio subida logo (configuración) |
| `API_BASE_URL` | URL base API (opcional) |
