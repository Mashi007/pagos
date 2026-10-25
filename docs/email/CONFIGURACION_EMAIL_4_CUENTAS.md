# Configuración de 4 cuentas de email

## Resumen

- **Cuenta 1**: Cobros (`/pagos/rapicredit-cobros`)
- **Cuenta 2**: Estado de cuenta (`/pagos/rapicredit-estadocuenta`)
- **Cuentas 3 y 4**: Notificaciones (`/pagos/notificaciones`); cada pestaña puede usar cuenta 3 o 4.

## Backend (implementado)

### Modelo de datos (BD, clave `email_config`)

- **Versión 1 (legacy)**: un solo bloque plano (smtp_host, smtp_user, …). Se migra automáticamente a v2 al leer.
- **Versión 2**:  
  `{ "version": 2, "cuentas": [ c1, c2, c3, c4 ], "asignacion": { "cobros": 1, "estado_cuenta": 2, "notificaciones_tab": { "dias_5": 3, "hoy": 3, … } } }`

### API

- **GET `/api/v1/configuracion/email/cuentas`**  
  Devuelve `{ version: 2, cuentas: [ … ], asignacion: { … } }`. Contraseñas enmascaradas.

- **PUT `/api/v1/configuracion/email/cuentas`**  
  Body: `{ cuentas: [ CuentaEmail, … ], asignacion: { cobros: 1, estado_cuenta: 2, notificaciones_tab: { … } }, … }`.  
  Valida, encripta y persiste en BD.

Los endpoints antiguos **GET/PUT `/configuracion/email/configuracion`** siguen funcionando (una sola cuenta); para la UI de 4 cuentas se usan los nuevos.

### Uso por servicio

- **Cobros**: usa siempre cuenta 1 (`servicio="cobros"`).
- **Estado de cuenta**: usa siempre cuenta 2 (`servicio="estado_cuenta"`).
- **Notificaciones**: por pestaña según `asignacion.notificaciones_tab` (p. ej. `dias_5` → 3, `mora_90` → 4). Se pasa `servicio="notificaciones"` y `tipo_tab` (dias_5, hoy, dias_1_retraso, etc.).

### Archivos tocados

- `app/core/email_cuentas.py`: modelo, migración v1→v2, `obtener_indice_cuenta`.
- `app/core/email_config_holder.py`: `_cuentas_data`, `get_smtp_config(servicio, tipo_tab)`, `update_from_api` v2, `sync_from_db` descifrado v2.
- `app/core/email.py`: `send_email(..., tipo_tab=...)` y uso de `get_smtp_config(servicio, tipo_tab)`.
- `app/api/v1/endpoints/notificaciones_tabs.py`: envío con `tipo_tab` para usar la cuenta asignada.
- `app/api/v1/endpoints/configuracion_email_cuentas.py`: GET/PUT `/cuentas`.
- `app/api/v1/endpoints/configuracion.py`: inclusión del router de cuentas.

## Frontend (pendiente)

1. **Configuración > Email**
   - Consumir **GET/PUT `/configuracion/email/cuentas`**.
   - UI con 4 bloques (Cuenta 1–4), cada uno con SMTP/IMAP (y opcionalmente “Probar” por cuenta).
   - Asignación fija: Cobros = 1, Estado de cuenta = 2.
   - Para Notificaciones: en la misma pantalla o en Notificaciones, selector por pestaña: “Usar cuenta: 3 / 4” y guardar en `asignacion.notificaciones_tab`.

2. **Notificaciones** (`/pagos/notificaciones`)
   - Por cada pestaña (Faltan 5 días, Hoy vence, Retrasadas, etc.), selector “Cuenta de correo: Cuenta 3 | Cuenta 4”.
   - Al guardar “Configuración de envíos” (o equivalente), persistir en backend la asignación por pestaña (ya soportada por PUT `/cuentas` con `asignacion.notificaciones_tab`).

## Nota sobre el ID "51290debb83a53b1b1c3bd476311fccc"

Ese valor no aparece en el código; la configuración de email se identifica en BD por la clave `email_config`. Si ese ID es de otro sistema (p. ej. frontend o integración), hay que mapearlo a la clave `email_config` en este backend.
