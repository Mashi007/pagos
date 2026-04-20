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

| Variable | Descripción |
|----------|-------------|
| `WHATSAPP_VERIFY_TOKEN` | Token verificación webhook |
| `WHATSAPP_ACCESS_TOKEN` | Access Token Meta |
| `WHATSAPP_PHONE_NUMBER_ID` | Phone Number ID |
| `WHATSAPP_BUSINESS_ACCOUNT_ID` | Business Account ID |
| `WHATSAPP_APP_SECRET` | App Secret (verificar firma webhooks) |
| `WHATSAPP_GRAPH_URL` | URL API (default graph.facebook.com/v18.0) |
| `ALERT_WEBHOOK_URL` | URL alertas (ej. Slack) cuando falla webhook |
| `SUPPORT_PHONE` | Teléfono soporte (estado ERROR_MAX_INTENTOS) |
| `MESSAGE_DELAY_SECONDS` | Segundos entre mensajes del bot |

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
| `GOOGLE_REDIRECT_URI` | Redirect URI tras autorizar Gmail |
| `GMAIL_TOKENS_PATH` | Ruta JSON tokens Gmail |
| `GEMINI_API_KEY` | API Key Gemini |
| `GEMINI_MODEL` | Modelo Gemini (ej. gemini-2.5-flash) |
| `DRIVE_ROOT_FOLDER_ID` | ID carpeta raíz Drive |
| `PAGOS_GMAIL_SCHEDULED_SCAN_ENABLED` | `true`/`false`: escaneo programado a las **4:00, 11:00 y 20:00** (America/Caracas), solo correos sin estrella ni etiquetas IMAGEN 1/2/3 (default true) |
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
