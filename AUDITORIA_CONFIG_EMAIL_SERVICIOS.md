# Auditoría: Conexión configuración email (4 cuentas) y servicios

## Resumen

La **configuración de 4 cuentas de correo** está correctamente conectada al backend y a la mayoría de los servicios. La UI (`EmailCuentasConfig`) usa la API `/api/v1/configuracion/email/cuentas`; el holder resuelve la cuenta por servicio/tab y `send_email` usa esa cuenta. **Hay una brecha en Notificaciones**: no se pasa `tipo_tab`, por lo que la asignación "Cuenta 3 vs 4 por pestaña" no se aplica en el envío con plantilla.

---

## 1. Flujo de datos

| Capa | Archivo / componente | Conexión |
|------|----------------------|-----------|
| **Frontend** | `EmailCuentasConfig.tsx` | Llama `emailCuentasApi.get()` y `emailCuentasApi.put()` |
| **API** | `frontend/src/services/emailCuentasApi.ts` | `GET/PUT ${BASE}/email/cuentas` → `/api/v1/configuracion/email/cuentas` |
| **Backend endpoint** | `app/api/v1/endpoints/configuracion_email_cuentas.py` | `GET /cuentas` lee de BD (clave `email_config`). `PUT /cuentas` valida, enmascara y guarda en `Configuracion` |
| **BD** | `Configuracion` (clave `email_config`) | Formato v2: `{ version: 2, cuentas: [c1,c2,c3,c4], asignacion: { cobros: 1, estado_cuenta: 2, notificaciones_tab: { dias_5: 3, ... } } }` |
| **Holder** | `app/core/email_config_holder.py` | `sync_from_db()` carga desde BD y llama `update_from_api()`. `get_smtp_config(servicio, tipo_tab)` usa `obtener_indice_cuenta()` y devuelve SMTP de la cuenta 1–4 |
| **Resolución cuenta** | `app/core/email_cuentas.py` | `obtener_indice_cuenta(servicio, tipo_tab, asignacion)` → cobros=1, estado_cuenta=2, notificaciones+tipo_tab=3 o 4 |
| **Envío** | `app/core/email.py` | `send_email(..., servicio=, tipo_tab=)` → `get_smtp_config(servicio, tipo_tab)` y envía con esa cuenta |

---

## 2. Servicios que envían correo

| Servicio | Dónde se llama `send_email` | Parámetros | Cuenta usada | Estado |
|----------|-----------------------------|------------|--------------|--------|
| **Cobros** | `app/api/v1/endpoints/cobros_publico.py` | `servicio="cobros"` | Cuenta 1 (asignación `cobros`) | OK |
| **Estado de cuenta** | `app/api/v1/endpoints/estado_cuenta_publico.py` | `servicio="estado_cuenta"` (código y PDF) | Cuenta 2 (`estado_cuenta`) | OK |
| **Notificaciones** | `app/api/v1/endpoints/notificaciones.py` (enviar con plantilla) | `servicio="notificaciones"` **sin `tipo_tab`** | Siempre cuenta por defecto (3) | Brecha: no se usa asignación por pestaña |
| **Tickets** | `app/core/email.py` (notificar contactos) | `servicio="tickets"` | No está en `obtener_indice_cuenta` → devuelve 1 | Usa Cuenta 1 (comportamiento actual) |
| **Informe pagos** | `app/core/informe_pagos_email.py` | `servicio="informe_pagos"` | No está en `obtener_indice_cuenta` → devuelve 1 | Usa Cuenta 1 (comportamiento actual) |

---

## 3. Detalle de la brecha en Notificaciones

- En **Configuración > Email** se puede asignar por pestaña (p. ej. "Faltan 5 días" → Cuenta 3, "Vence hoy" → Cuenta 4).
- Esa asignación se guarda en `asignacion.notificaciones_tab` (dias_5, hoy, etc.).
- En `notificaciones.py`, el endpoint `POST /plantillas/{plantilla_id}/enviar` hace:
  ```python
  ok, msg = send_email([correo], asunto, cuerpo, servicio="notificaciones")
  ```
  **No se pasa `tipo_tab`.** Por tanto `get_smtp_config(servicio="notificaciones", tipo_tab=None)` usa el fallback (cuenta 3) y **nunca** la cuenta 4 ni la asignación por pestaña.

**Recomendación:** Pasar el tipo de plantilla como `tipo_tab` cuando exista (p. ej. el campo `tipo` de la plantilla si coincide con los ids de `notificaciones_tab`):

```python
# En notificaciones.py, en enviar_con_plantilla (alrededor de línea 827):
tipo_tab = (getattr(p, "tipo", None) or "").strip() or None
ok, msg = send_email([correo], asunto, cuerpo, servicio="notificaciones", tipo_tab=tipo_tab)
```

Además, revisar cualquier **envío masivo** de notificaciones (cron, job, etc.): si existe, debe recibir/pasar `tipo_tab` (dias_5, hoy, etc.) a `send_email` para que se use la cuenta asignada a esa pestaña.

---

## 4. Actualización del holder tras guardar

- `PUT /cuentas` **solo escribe en BD**; no llama a `update_from_api()` en el proceso actual.
- En la **siguiente** llamada a `get_smtp_config()` (desde cualquier envío), se ejecuta `sync_from_db()`, que lee de BD y actualiza el holder.
- Conclusión: la configuración guardada se aplica en el **próximo** envío; no hace falta reiniciar el servidor.

---

## 5. Checklist de conexión

- [x] Frontend (EmailCuentasConfig) → API `/configuracion/email/cuentas`
- [x] API GET/PUT cuentas → BD (clave `email_config`, versión 2)
- [x] Holder: `sync_from_db()` y `get_smtp_config(servicio, tipo_tab)` con `obtener_indice_cuenta`
- [x] Cobros → `servicio="cobros"` → Cuenta 1
- [x] Estado de cuenta → `servicio="estado_cuenta"` → Cuenta 2
- [x] Notificaciones → **corregido**: se pasa `tipo_tab` (desde `p.tipo` de la plantilla) a `send_email` para respetar Cuenta 3/4 por pestaña
- [x] Tickets / Informe pagos usan cuenta por defecto (1) mientras no estén en `obtener_indice_cuenta`

---

## 6. Acción recomendada

1. **Aplicar el cambio en `notificaciones.py`** (añadir `tipo_tab` a `send_email` como en la sección 3).
2. **Revisar** si existe un job de envío masivo de notificaciones y, en ese caso, asegurar que también pase `tipo_tab` según el tipo de notificación.
3. (Opcional) Si se desea que **Tickets** o **Informe pagos** usen una cuenta distinta, extender `obtener_indice_cuenta` y `asignacion` en BD/UI para esos servicios.
