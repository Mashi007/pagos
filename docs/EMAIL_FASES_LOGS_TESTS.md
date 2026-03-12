# Fases, logs y tests del flujo de email

Documento de referencia para **indicadores por fase** (fallas o funcionamiento) en configuración y envío de email.

## Fases definidas

| Fase (constante) | Descripción | Dónde se registra |
|------------------|-------------|-------------------|
| `email_fase_config_carga` | Carga de configuración desde BD | `email_config_holder.sync_from_db()` |
| `email_fase_config_guardado` | Guardado de configuración en BD | PUT `/configuracion/email/configuracion` |
| `email_fase_modo_pruebas` | Decisión modo pruebas (redirección destinos) | `email.send_email()` |
| `email_fase_smtp_config` | Validación SMTP (host, usuario, contraseña) | `email.send_email()` |
| `email_fase_smtp_conexion` | Conexión TCP/TLS al servidor SMTP | `email.send_email()` |
| `email_fase_smtp_envio` | Envío del mensaje (éxito o fallo) | `email.send_email()` |
| `email_fase_imap_conexion` | Conexión TCP/SSL IMAP | `email.test_imap_connection()` |
| `email_fase_imap_login` | Login IMAP | `email.test_imap_connection()` |
| `email_fase_imap_list` | Listado de carpetas IMAP | `email.test_imap_connection()` |
| `email_fase_imap_completa` | Prueba IMAP completa (éxito o fallo) | `email.test_imap_connection()` |

## Formato de log

Cada fase se registra con `log_phase()` en formato:

```
[FASE] phase=<nombre_fase> | success=<True|False> | <mensaje> | duration_ms=<opcional> | <extra>
```

- **success=True**: paso correcto (INFO).
- **success=False**: fallo en esa fase (WARNING).
- **duration_ms**: tiempo del paso en milisegundos cuando aplica.

Así se puede localizar en logs (p. ej. Render) en qué fase falló un envío o una prueba IMAP.

## Dónde se usan

- **Backend**
  - `app/core/email_phases.py`: constantes y `log_phase()` / `log_phase_exception()`.
  - `app/core/email_config_holder.py`: `FASE_CONFIG_CARGA` en `sync_from_db()`.
  - `app/core/email.py`: fases SMTP e IMAP en `send_email()` y `test_imap_connection()`.
  - `app/api/v1/endpoints/configuracion_email.py`: `FASE_CONFIG_GUARDADO` en PUT config.

## Tests

Archivo: **`backend/tests/test_config_email_fases.py`**.

- **Endpoints**: GET/PUT configuración email, GET estado, POST probar, POST probar-imap (con mocks de `send_email` y `test_imap_connection`).
- **Indicadores**: comprobación de que las constantes de fase existen y que `log_phase()` escribe el formato esperado (`[FASE]`, `phase=`, `success=`).

Ejecución:

```bash
cd backend
python -m pytest tests/test_config_email_fases.py -v
```

## Cómo usar en producción

1. **Fallo en envío**: buscar en logs `[FASE]` y `success=False`; el valor de `phase=` indica la etapa (config, smtp_config, smtp_conexion, smtp_envio).
2. **Fallo en prueba IMAP**: buscar `email_fase_imap_completa` con `success=False` y el mensaje asociado.
3. **Métricas**: opcionalmente parsear líneas `[FASE]` para contar éxitos/fallos por fase o por `duration_ms`.
