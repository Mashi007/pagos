# Matriz de verificación: correo por servicio

Documento de auditoría: cómo comprobar que cada **servicio** puede enviar correo, qué interruptores aplican y qué buscar en logs (Render / consola backend).

## Reglas globales (siempre)

| Concepto | Dónde se guarda | Efecto |
|----------|-----------------|--------|
| **Correo maestro** | `email_activo` (`"true"` / `"false"`) | Si es `false`, **ningún** servicio envía correo vía `get_email_activo_servicio(...)`. |
| **On/Off por servicio** | `email_activo_<servicio>` | Si el maestro está activo y el flag del servicio es `false`, ese servicio no envía. |
| **Modo pruebas** | `modo_pruebas` + `modo_pruebas_<servicio>` + `email_pruebas` | Puede redirigir destinos al correo de pruebas (según lógica en `send_email` / holder). |

Servicios reconocidos en código (`EMAIL_SERVICES` en `app/core/email_config_holder.py`):

`notificaciones`, `informe_pagos`, `estado_cuenta`, `cobros`, `campanas`, `tickets`.

---

## Evidencia típica en logs

Buscar en orden:

1. `[FASE] phase=email_fase_modo_pruebas` — modo pruebas / servicio.
2. `[FASE] phase=email_fase_smtp_config` — host/puerto presentes.
3. `[FASE] phase=email_fase_smtp_conexion` — TLS / conexión OK.
4. `[FASE] phase=email_fase_smtp_envio` — resultado del envío.
5. `[SMTP_ENVIO] estado=aceptado ... servicio=<servicio> tipo_tab=<tab o vacío> ...` — SMTP aceptó el mensaje.
6. Errores: `[SMTP_ENVIO] estado=error_excepcion` o `estado=abortado razon=...`.

Para envíos masivos de notificaciones, además:

- `[notif_envio_email] Email enviado` / `Email fallido`
- `[notif_envio_resumen] Resumen: enviados=... fallidos=...`

---

## Matriz por servicio

### 1. Cobros (`cobros`)

| Qué validar | Cómo probar (sugerido) | Logs / señales |
|-------------|------------------------|----------------|
| SMTP cuenta asignada (Cuenta 1 en config v2) | Configuración → Email → **Enviar prueba** (incluye cuenta 1) o prueba SMTP legacy | `[SMTP_ENVIO] ... servicio=cobros` |
| Recibo / flujo interno | Aprobar pago reportado con correo cliente, o **Enviar recibo** manual | `[COBROS] enviar-recibo ref=...` y `servicio=cobros` |
| Prueba desde pantalla legacy | Endpoint de prueba en `configuracion_email` (usa `servicio="cobros"`) | Mismo patrón `servicio=cobros` |

**Bloqueo esperado:** si `get_email_activo_servicio("cobros")` es false → el endpoint de negocio responde 400 y **no** llama a `send_email` (ver `cobros.py`).

---

### 2. Estado de cuenta (`estado_cuenta`)

| Qué validar | Cómo probar | Logs / señales |
|-------------|-------------|----------------|
| Código / PDF | Flujo público estado de cuenta que envía email (cuando el flag está activo) | `servicio=estado_cuenta` |
| Cuenta SMTP | Prueba masiva **Cuenta 2** | `[SMTP_ENVIO] ... servicio=estado_cuenta` |

**Bloqueo esperado:** rutas que respetan `get_email_activo_servicio("estado_cuenta")` no envían si está desactivado.

---

### 3. Notificaciones (`notificaciones`)

Incluye **pestañas** (`tipo_tab`: `dias_5`, `dias_3`, `dias_1`, `hoy`, `dias_1_retraso`, etc.) y asignación **Cuenta 3 / 4**.

| Qué validar | Cómo probar | Logs / señales |
|-------------|-------------|----------------|
| SMTP por pestaña | **Enviar prueba** masiva (cuentas 3 y 4 según asignación) | `servicio=notificaciones tipo_tab=<tab>` |
| Envío masivo UI | Notificaciones → envío masivo (según configuración guardada) | `[notif_envio_email]`, `[notif_envio_resumen]` |
| Plantilla prueba | Endpoint de prueba con plantilla + `tipo_tab` de plantilla | `servicio=notificaciones` y `tipo_tab` si aplica |
| Liquidados | Job/servicio que usa `tipo_tab=liquidados` | `servicio=notificaciones tipo_tab=liquidados` + `[LIQUIDADO_NOTIF]` |

---

### 4. Informe de pagos (`informe_pagos`)

| Qué validar | Cómo probar | Logs / señales |
|-------------|-------------|----------------|
| Envío programado | Disparar el job / función que llama `informe_pagos_email` | `Informe pagos enviado` o `Informe pagos: envio de email desactivado` |
| SMTP | Misma cuenta base que resuelve `get_smtp_config(servicio="informe_pagos")` | `servicio=informe_pagos` en `[SMTP_ENVIO]` |

Antes de enviar, el código comprueba `get_email_activo_servicio("informe_pagos")` y sale sin enviar si está off.

---

### 5. Campañas CRM (`campanas`)

| Qué validar | Cómo probar | Logs / señales |
|-------------|-------------|----------------|
| Envío de campaña | Ejecutar campaña que envía correos (endpoint CRM campañas) | `servicio=campanas` |

---

### 6. Tickets (`tickets`)

| Qué validar | Cómo probar | Logs / señales |
|-------------|-------------|----------------|
| Notificación ticket / informe | Crear ticket o flujo que dispare email a contactos configurados | `servicio=tickets` |
| Funciones en `email.py` | `notify_ticket_created` usa `servicio="tickets"` | Mismo patrón en logs |

---

## Rutas que envían **sin** pasar por `get_email_activo_servicio` (diagnóstico)

Útiles para validar SMTP; **no** sustituyen el corte del maestro en flujos de negocio:

- `POST .../configuracion/email/enviar-prueba` (prueba multi-cuenta): llama `send_email` directamente.
- Pruebas SMTP desde endpoints de configuración legacy (`configuracion_email`).

Si necesitas **cero envíos** en producción, además del maestro en `false`, evita ejecutar esas pruebas.

---

## Checklist rápido (producción)

1. UI: **Correo maestro** = Activo (si quieres envíos reales).
2. UI: cada **servicio** necesario = Activo.
3. **Correo de pruebas** válido si usas modo pruebas.
4. Ejecutar **Enviar prueba** (4 cuentas) y confirmar en logs `estado=aceptado` para cada cuenta probada.
5. Opcional: un envío real acotado por servicio (p. ej. un recibo, una notificación de prueba).

---

*Última actualización: generada para auditoría interna del repositorio.*
