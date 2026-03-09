# Validación de variables de entorno (backend en Render)

Comprobación según el código y las variables que usas en Render.

---

## Crítico: corregir

### 1. `GOOGLE_REDIRECT_URI`

- **Debe ser exactamente** la URL del callback de OAuth (mismo host que el backend y path correcto).
- **Path correcto:** `/api/v1/configuracion/informe-pagos/google/callback`  
  (es **informe-pagos**, no `informe-pages`).
- **Host correcto:** el mismo que sirve tu API (ej. `rapicredit.onrender.com`), no `apicredit.onrender.com`.

**Valor recomendado** (si el backend es `https://rapicredit.onrender.com`):

```env
GOOGLE_REDIRECT_URI=https://rapicredit.onrender.com/api/v1/configuracion/informe-pagos/google/callback
```

- Si tienes `informe-pages` → cambiar a **informe-pagos**.
- Si tienes `apicredit.onrender.com` → cambiar a **rapicredit.onrender.com** (o al host real de tu backend).

Esa misma URL debe estar registrada en **Google Cloud Console** > Credenciales > URIs de redirección autorizados.

---

### 2. Nombre completo de variables Gmail/Gemini

El backend solo reconoce estos nombres (sensible a mayúsculas/minúsculas):

| Variable | Nombre completo | Valor que tienes |
|----------|-----------------|-------------------|
| Cron cada N min | `PAGOS_GMAIL_CRON_MINUTES` | 30 ✓ |
| Pausa entre llamadas Gemini | `PAGOS_GMAIL_DELAY_BETWEEN_GEMINI_SECONDS` | 4 ✓ |
| Máx. correos por ejecución | `PAGOS_GMAIL_MAX_EMAILS_PER_RUN` | 15 ✓ |

Si en Render la variable de la pausa está como **PAGOS_GMAIL_DELAY_BETWEEN_GET_EMAILS** (u otro nombre distinto), no tendrá efecto. Debe ser exactamente:

```env
PAGOS_GMAIL_DELAY_BETWEEN_GEMINI_SECONDS=4
PAGOS_GMAIL_MAX_EMAILS_PER_RUN=15
```

---

## Recomendado

### 3. CORS

- El backend usa solo **`CORS_ORIGINS`** (no usa `ALLOWED_ORIGINS`).
- Si el frontend está en `https://rapicredit-frontend.onrender.com`, incluye ambos orígenes:

```env
CORS_ORIGINS=https://rapicredit.onrender.com,https://rapicredit-frontend.onrender.com
```

O en JSON:

```env
CORS_ORIGINS=["https://rapicredit.onrender.com","https://rapicredit-frontend.onrender.com"]
```

### 4. `BACKEND_PUBLIC_URL` y OAuth

- Si no está definida, el backend deduce la base desde `GOOGLE_REDIRECT_URI`.
- Para evitar confusiones, conviene fijarla:

```env
BACKEND_PUBLIC_URL=https://rapicredit.onrender.com
```

(Sin barra final.)

### 5. Sentry

- `SENTRY_DSN=https://tu-sentry-dsn` es un placeholder.
- Si no usas Sentry, puedes dejarla o borrarla.
- Si usas Sentry, sustituir por el DSN real del proyecto.

---

## Resumen de variables vistas en tus capturas

| Variable | Estado | Nota |
|----------|--------|------|
| ADMIN_EMAIL, ADMIN_PASSWORD | OK | |
| CORS_ORIGINS | Revisar | Incluir también frontend si aplica |
| ALLOWED_ORIGINS | No usada | El backend solo usa CORS_ORIGINS |
| DATABASE_URL, DB_* | OK | |
| DEBUG=false, ENVIRONMENT=production | OK | |
| GEMINI_API_KEY | OK | |
| GOOGLE_REDIRECT_URI | Corregir | informe-**pagos** y host correcto (rapicredit) |
| PAGOS_GMAIL_CRON_MINUTES=30 | OK | |
| PAGOS_GMAIL_DELAY_BETWEEN_GE... | Verificar nombre | Debe ser PAGOS_GMAIL_DELAY_BETWEEN_**GEMINI**_SECONDS |
| PAGOS_GMAIL_MAX_EMAILS_PER_RUN=15 | OK | |
| SENTRY_DSN | Placeholder | Sustituir o quitar si no usas Sentry |
| WHATSAPP_* | OK | Si usas WhatsApp |
| RATE_LIMIT_*, REDIS_URL, UVICORN_* | OK | |

---

## Cómo comprobar tras cambiar

1. **OAuth / Gmail:** Ir a Configuración > Informe de pagos, pulsar «Conectar con Google» y completar el flujo; no debe dar error de redirect.
2. **Gemini:** `GET https://rapicredit.onrender.com/api/v1/health/gemini` (o `/health/gemini`) y revisar que no haya 429 por cuota (ya hay reintentos en código).
3. **CORS:** Que el frontend en `rapicredit-frontend.onrender.com` pueda llamar a la API sin error de CORS.
