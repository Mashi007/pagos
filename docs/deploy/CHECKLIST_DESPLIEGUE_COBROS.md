# Checklist de despliegue – Módulo Cobros

Antes de dar el enlace público del formulario de reporte de pago a los clientes, verificar lo siguiente.

## 1. Variables de entorno obligatorias

| Variable | Uso | Riesgo si falta |
|----------|-----|------------------|
| `GEMINI_API_KEY` | Comparación formulario vs imagen (100% → aprobado automático) | Todos los reportes van a **en_revision**; no hay fallo visible para el cliente, pero aumenta carga manual. |
| `DATABASE_URL` | Persistencia de reportes, clientes, préstamos | El reporte falla con error 500. |
| SMTP | Envío de recibo al aprobar y de correo al rechazar | Recibo/PDF se genera y guarda en BD, pero el cliente **no recibe el correo**. |

### SMTP

Puede configurarse de dos formas:

- **Variables de entorno:** `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`
- **Configuración > Email** en el dashboard (persistido en BD). Si está guardado, tiene prioridad sobre .env.

Ambas deben tener al menos: servidor (host), usuario y contraseña. Para Gmail usar **Contraseña de aplicación** (App Password).

## 2. Verificación rápida (health)

- **`GET /api/v1/health`** – API viva.
- **`GET /api/v1/health/db`** – BD conectada y tablas críticas (incluye `pagos_reportados`, `usuarios`).
- **`GET /api/v1/health/cobros`** – Módulo Cobros listo:
  - `db_ok`: BD accesible.
  - `gemini_configured`: `GEMINI_API_KEY` configurado (no se expone el valor).
  - `smtp_configured`: SMTP con host, usuario y contraseña no vacíos.

Si `status` es `degraded` o `error`, revisar las variables y la configuración de email antes de usar el formulario público.

## 3. Modo pruebas de correo

Si en **Configuración > Email** está activo el “modo pruebas”, los correos se redirigen al correo de pruebas. En producción, comprobar que:

- El modo pruebas esté desactivado, o
- El correo de pruebas sea el adecuado para validar envíos antes de dar el link a clientes.

## 4. Enlace público canónico

Usar una sola URL en comunicaciones (SMS, correos, carteles):

- Ejemplo: `https://rapicredit.onrender.com/pagos/rapicredit` (o el dominio definitivo).

El path canónico está definido en el frontend (`PUBLIC_REPORTE_PAGO_PATH = 'rapicredit'`). No difundir solo `/reporte-pago` para evitar dos URLs de referencia.

## 5. Alertas recomendadas

Configurar alertas (Render, Uptime Robot, etc.) sobre:

- `GET /api/v1/health` (API viva).
- `GET /api/v1/health/db` (status distinto de "ok" o tablas faltantes).
- `GET /api/v1/health/cobros` (status `degraded` o `error` si se usa este endpoint).

## 6. Resumen

- [ ] `GEMINI_API_KEY` configurado en producción.
- [ ] `DATABASE_URL` correcta y accesible.
- [ ] SMTP configurado (env o Configuración > Email) y probado.
- [ ] Modo pruebas desactivado o correo de pruebas adecuado.
- [ ] Health `/health/db` y, opcionalmente, `/health/cobros` verificados.
- [ ] Enlace público único (`/pagos/rapicredit`) definido y usado en comunicaciones.

Implementar las de prioridad alta (Gemini, BD, SMTP) y revisar el resultado de `send_email` en aprobado/rechazo (logs y mensaje al usuario si falla el envío) da una base sólida para que el módulo Cobros funcione bien en producción.
