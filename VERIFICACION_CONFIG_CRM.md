# Verificación: Configuración (Email y WhatsApp) integrada al CRM

**Fecha:** 2025-02-02  
**Reglas de referencia:** `INTEGRACION_CONFIG_CRM.md`, `AUDITORIA_CONFIGURACION.md`, datos reales desde BD.

---

## 1. Resumen

| Área | Estado | Notas |
|------|--------|--------|
| **Configuración Email → Notificaciones (CRM)** | ✅ Integrada | Envío usa config guardada en BD vía `sync_from_db()` antes de cada `send_email()`. |
| **Configuración Email → Tickets (CRM)** | ✅ Integrada | `notify_ticket_created/updated` usan `get_tickets_notify_emails()` desde holder (BD). |
| **Configuración WhatsApp → Comunicaciones (CRM)** | ✅ Integrada* | UI muestra estado y enlace a Config > WhatsApp; envío/recepción usan config desde BD (holder). |
| **Enlaces CRM → Módulo Configuración** | ✅ Correctos | Notificaciones → `/configuracion?tab=email`; Comunicaciones → `/configuracion?tab=whatsapp`. |
| **Persistencia** | ✅ BD | `email_config` y `whatsapp_config` en tabla `configuracion`; sin hardcodear datos demo. |

\* Tras implementar `whatsapp_config_holder` y uso en `whatsapp_service` y webhook (ver sección 3).

---

## 2. Verificación por reglas

### 2.1 Notificaciones (CRM)

- **Frontend:** Página Notificaciones (`/notificaciones`) con pestaña **Configuración** que:
  - Carga/guarda configuración de envíos vía `emailConfigService.obtenerConfiguracionEnvios()` / `actualizarConfiguracionEnvios()` → `GET/PUT /api/v1/configuracion/notificaciones/envios`.
  - Muestra card con texto: *"Los correos de notificaciones usan la configuración de Gmail/SMTP guardada en Configuración > Email"* y enlace **"Configurar en Configuración (Email)"** → `/configuracion?tab=email`.
- **Backend:** `notificaciones_tabs.py` usa `send_email()` de `app.core.email`. En `email.py`, `send_email()` llama a `sync_from_db()` antes de enviar, por lo que los correos usan la **configuración guardada en Configuración > Email** (tabla `configuracion`, clave `email_config`), no solo .env.

**Conclusión:** La configuración Email está **bien integrada** con Notificaciones (CRM).

### 2.2 Comunicaciones (CRM)

- **Frontend:** Página Comunicaciones (`/comunicaciones`) obtiene configuración WhatsApp con `whatsappConfigService.obtenerConfiguracionWhatsApp()` → `GET /api/v1/configuracion/whatsapp/configuracion`. Muestra estado (`configurada`) y enlace **"Configurar en Configuración (WhatsApp)"** → `/configuracion?tab=whatsapp`.
- **Backend (antes de holder):** El webhook y `whatsapp_service` leían token/URL desde `settings` (.env). La config en BD se usaba solo para la UI.
- **Backend (con holder):** Se añade `whatsapp_config_holder` con `sync_from_db()`; el servicio de WhatsApp y la verificación del webhook usan la config cargada desde BD (clave `whatsapp_config`), de forma análoga a Email.

**Conclusión:** Tras el holder, la configuración WhatsApp queda **bien integrada** con Comunicaciones (CRM).

### 2.3 Módulo de Configuración (Email y WhatsApp)

- **Email:** Endpoints en `configuracion_email.py` (GET/PUT `/configuracion`, GET `/estado`, POST `/probar`, `/probar-imap`). Persistencia en BD (`email_config`). PUT actualiza `email_config_holder` vía `update_from_api()`. Contraseñas enmascaradas en GET; no se sobrescriben con "***" en PUT.
- **WhatsApp:** Endpoints en `configuracion_whatsapp.py` (GET/PUT `/configuracion`). Persistencia en BD (`whatsapp_config`). PUT debería actualizar un holder si se usa en tiempo real; el holder se sincroniza desde BD antes de cada uso (webhook, envío).

### 2.4 Enlaces y rutas

- Sidebar: "Configuración Email" → `/configuracion?tab=email`, "Configuración WhatsApp" → `/configuracion?tab=whatsapp`.
- Constantes: `configuracionSecciones.ts` define `emailConfig`, `whatsappConfig` y `NOMBRES_SECCION_ESPECIAL` para abrir la pestaña correcta.

---

## 3. Implementación: WhatsApp desde BD (alineado con Email)

Para que la configuración guardada en **Configuración > WhatsApp** sea la usada por el CRM (Comunicaciones, webhook, envío):

1. **`app/core/whatsapp_config_holder.py`** (nuevo):
   - `sync_from_db()`: carga desde tabla `configuracion` (clave `whatsapp_config`) y actualiza un diccionario en memoria.
   - `get_whatsapp_config()`: devuelve `api_url`, `access_token`, `phone_number_id`, `webhook_verify_token`, etc. (con fallback a `settings` si no hay nada en BD).
   - No exponer tokens en logs.

2. **`app/services/whatsapp_service.py`**:
   - Antes de usar token/URL (p. ej. en `_process_image_message`), llamar a `sync_from_db()` y obtener config con `get_whatsapp_config()`.

3. **`app/api/v1/endpoints/whatsapp.py`** (webhook):
   - En `verify_webhook`: obtener `webhook_verify_token` desde el holder (que hace `sync_from_db()`), no solo desde `settings`.
   - Cualquier uso de token/URL para llamadas a Meta debe usar el holder.

4. **`app/api/v1/endpoints/configuracion_whatsapp.py`**:
   - Tras PUT, opcionalmente actualizar el holder en memoria para no esperar al próximo `sync_from_db()` (consistencia con `configuracion_email` que llama a `update_from_api`).

Con esto, la configuración cuando se implemente en el módulo de configuración (Email y WhatsApp) queda **bien integrada al CRM** (notificaciones, comunicaciones) según las reglas.

---

## 4. Notificaciones: integración Email, WhatsApp y get_db (reglas de negocio)

- **get_db:** Todos los endpoints de Notificaciones inyectan `db: Session = Depends(get_db)` (lista, resumen, clientes-retrasados, actualizar, pestañas GET/POST enviar). Los datos vienen de BD (cuotas, clientes, configuracion).
- **Configuración de envíos (notificaciones_envios):** Cargada desde BD en cada POST `/enviar` vía `get_notificaciones_envios_config(db)`. Por cada tipo (PAGO_5_DIAS_ANTES, PAGO_DIA_0, PREJUDICIAL, MORA_61, etc.) se respeta `habilitado` (si false no se envía) y `cco` (se añade al correo).
- **Email:** Envío con `send_email()` (sync_from_db en core/email); CCO por tipo soportado en `send_email(..., cc_emails=...)`.
- **WhatsApp:** Envío con `send_whatsapp_text()` (app/core/whatsapp_send.py) usando config desde BD (whatsapp_config_holder). Si el item tiene `telefono`, se envía el mismo cuerpo por WhatsApp. Respuesta incluye `enviados_whatsapp`, `fallidos_whatsapp`.

Con esto Notificaciones cumple procesos y reglas de negocio: datos reales desde BD, config desde BD, canales Email y WhatsApp integrados a Configuración.

---

## 5. Checklist final

- [x] Notificaciones usan config Email desde BD (sync_from_db en send_email).
- [x] Notificaciones usan config envíos (habilitado/CCO) desde BD (notificaciones_envios).
- [x] Notificaciones envían por WhatsApp cuando hay teléfono (config desde Configuración > WhatsApp).
- [x] Todos los procesos de Notificaciones usan get_db (lista, resumen, tabs, enviar).
- [x] Tickets CRM usan contactos de notificación desde config Email (tickets_notify_emails).
- [x] Comunicaciones muestran estado WhatsApp y enlace a Configuración > WhatsApp.
- [x] WhatsApp webhook y servicio usan config desde BD vía whatsapp_config_holder.
- [x] Enlaces desde CRM (Notificaciones, Comunicaciones) a Configuración con `?tab=email` y `?tab=whatsapp`.
- [x] Persistencia en tabla `configuracion`; sin datos demo hardcodeados en endpoints de datos reales.
