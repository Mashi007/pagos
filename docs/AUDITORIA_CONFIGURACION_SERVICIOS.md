# Auditoría: Integración Configuración ↔ Servicios (AI, WhatsApp, Email)

**Objetivo:** Verificar que los servicios que requieren configuración (AI, WhatsApp, Email) están correctamente integrados con el módulo Configuración (persistencia en BD, uso de holders, sincronización antes de usar).

**Fecha:** 2026-02-02

---

## 1. Resumen ejecutivo

| Área | Estado | Notas |
|------|--------|--------|
| **AI (OpenRouter)** | ✅ Integrado | Config en BD (clave `configuracion_ai`). Carga con `_load_ai_config_from_db(db)` en GET/PUT/chat/probar. API key nunca expuesta al frontend. |
| **WhatsApp** | ✅ Integrado | Config en BD (clave `whatsapp_config`). Holder `whatsapp_config_holder` con `sync_from_db()` antes de cada uso. PUT actualiza BD y llama `whatsapp_sync_from_db()`. |
| **Email (SMTP)** | ✅ Integrado | Config en BD (clave `email_config`). Holder `email_config_holder` con `sync_from_db()` al inicio de `send_email()`. |
| **Informe pagos (Drive, Sheets, OCR)** | ✅ Integrado | Config en BD (clave `informe_pagos_config`). Holder `informe_pagos_config_holder` con `sync_from_db()` en servicios que la usan. Email del informe usa `email_config_holder` para SMTP. |

**Conclusión:** La integración entre Configuración y los servicios (AI, WhatsApp, Email, Informe pagos) es correcta. Los servicios que envían correo o mensajes WhatsApp cargan la configuración desde BD (vía sync/holder o `_load_*_from_db`) antes de usarla.

---

## 2. AI (OpenRouter)

### 2.1 Persistencia y API

- **Tabla:** `configuracion`, clave `configuracion_ai`.
- **Endpoints:** `GET/PUT /api/v1/configuracion/ai/configuracion`, `POST /api/v1/configuracion/ai/chat`, `POST /api/v1/configuracion/ai/probar`.
- **Archivo:** `backend/app/api/v1/endpoints/configuracion_ai.py`.

### 2.2 Carga de configuración

- **GET /configuracion:** `_load_ai_config_from_db(db)` → actualiza `_ai_config_stub` desde BD.
- **PUT /configuracion:** `_load_ai_config_from_db(db)`, actualiza stub, persiste en BD con `Configuracion(clave=CLAVE_AI, valor=json)`.
- **POST /chat:** `_load_ai_config_from_db(db)` al inicio → respuestas usan modelo/temperatura/max_tokens y API key desde stub (o env).
- **POST /probar:** `_load_ai_config_from_db(db)` al inicio.

### 2.3 API key

- Se persiste en BD (opcional) y/o se lee de `OPENROUTER_API_KEY` en entorno.
- `_get_openrouter_key()`: primero stub (BD), luego `settings.OPENROUTER_API_KEY`.
- En GET de configuración la clave **nunca** se devuelve al frontend (solo indicador de si está configurada).

### 2.4 Frontend

- **Configuración > AI:** `AIConfig.tsx` llama `GET/PUT /api/v1/configuracion/ai/configuracion`, `POST /api/v1/configuracion/ai/probar`, documentos, prompt, calificaciones.
- **Chat AI:** `ChatAI.tsx` usa `GET /api/v1/configuracion/ai/configuracion` y `POST /api/v1/configuracion/ai/chat`.
- **Comunicaciones:** Enlace a Configuración > AI (`/configuracion?tab=ai`).

---

## 3. WhatsApp

### 3.1 Persistencia y API

- **Tabla:** `configuracion`, clave `whatsapp_config`.
- **Endpoints:** `GET/PUT /api/v1/configuracion/whatsapp/configuracion`, `POST /api/v1/configuracion/whatsapp/probar`.
- **Archivo:** `backend/app/api/v1/endpoints/configuracion_whatsapp.py`.

### 3.2 Holder y sincronización

- **Holder:** `backend/app/core/whatsapp_config_holder.py`.
  - `sync_from_db()`: carga desde tabla `configuracion` (clave `whatsapp_config`) y actualiza `_current`.
  - `get_whatsapp_config()`: si `_current` vacío llama `sync_from_db()`; devuelve `api_url`, `access_token`, `phone_number_id`, etc.
- **PUT /configuracion:** después de guardar en BD llama `whatsapp_sync_from_db()` para que el holder refleje de inmediato la nueva config.

### 3.3 Servicios que usan WhatsApp

| Servicio / Endpoint | ¿Sync antes de usar? | Uso |
|---------------------|----------------------|-----|
| `core/whatsapp_send.send_whatsapp_text` | ✅ `whatsapp_sync_from_db()` luego `get_whatsapp_config()` | Envío desde Notificaciones, Comunicaciones, prueba desde Config. |
| `services/whatsapp_service._send_whatsapp_async` | ✅ `whatsapp_sync_from_db()` luego `get_whatsapp_config()` | Respuestas automáticas flujo cobranza (webhook). |
| `services/whatsapp_service._process_image_message` | ✅ `whatsapp_sync_from_db()` luego `get_whatsapp_config()` | Descarga de imagen Meta. |
| `api/v1/endpoints/whatsapp.py` (webhook GET/POST) | ✅ `whatsapp_sync_from_db()` antes de verificar token o procesar | Verificación webhook y firma. |

### 3.4 Tokenes sensibles

- `access_token` y `webhook_verify_token` no se exponen en GET (se devuelven como `***`).
- PUT no sobrescribe si el frontend envía `***` o vacío.

### 3.5 Frontend

- **Configuración > WhatsApp:** `WhatsAppConfig.tsx` usa `notificacionService.obtenerConfiguracionWhatsApp()` (GET) y actualizar (PUT).
- **Comunicaciones:** `ComunicacionesPage` usa `whatsappConfigService.obtenerConfiguracionWhatsApp()` para indicar si está configurado; enlaces a Configuración > WhatsApp, Email, AI, Informe pagos.

---

## 4. Email (SMTP)

### 4.1 Persistencia y API

- **Tabla:** `configuracion`, clave `email_config`.
- **Endpoints:** `GET/PUT /api/v1/configuracion/email/configuracion`, `GET /api/v1/configuracion/email/estado`, `POST /api/v1/configuracion/email/probar`, `POST /api/v1/configuracion/email/probar-imap`.
- **Archivo:** `backend/app/api/v1/endpoints/configuracion_email.py`.

### 4.2 Holder y sincronización

- **Holder:** `backend/app/core/email_config_holder.py`.
  - `sync_from_db()`: carga desde tabla `configuracion` (clave `email_config`) y llama `update_from_api(data)` para actualizar `_current`.
  - `get_smtp_config()`: devuelve config desde `_current` o, si no hay usuario, desde `settings` (.env).
  - `get_tickets_notify_emails()`: lista de emails para notificación de tickets (desde `_current` o env).
- **PUT /configuracion:** actualiza `_email_config_stub` en el endpoint y persiste en BD; **no** llama a `email_config_holder.update_from_api`. Los servicios que envían correo llaman `sync_from_db()` al inicio, por lo que la próxima vez que se use el holder se cargará desde BD.

### 4.3 Servicios que usan Email

| Servicio / Endpoint | ¿Sync antes de usar? | Uso |
|---------------------|----------------------|-----|
| `core/email.send_email` | ✅ `sync_from_db()` al inicio, luego `get_smtp_config()` | Cualquier envío SMTP. |
| `core/email.notificar_tickets_creado` / `notificar_tickets_actualizado` | ✅ Usan `send_email()` que hace `sync_from_db()` | Notificaciones de tickets. |
| `core/informe_pagos_email.enviar_informe_pagos_email` | ✅ `email_sync()` (alias de `sync_from_db`) al inicio, luego `send_email()` | Informe de pagos 6:00, 13:00, 16:30. |
| `api/v1/endpoints/configuracion_email.py` (POST probar) | ✅ Usa `send_email()` que hace `sync_from_db()` | Prueba de envío desde Config. |
| `api/v1/endpoints/notificaciones_tabs.py` | ✅ Usa `send_email()` que hace `sync_from_db()` | Envío por pestañas de notificaciones. |

### 4.4 Contraseñas

- En GET, `smtp_password` e `imap_password` se devuelven como `***`.

### 4.5 Frontend

- **Configuración > Email:** `EmailConfig.tsx` llama GET/PUT `/api/v1/configuracion/email/configuracion`, GET estado, POST probar.
- **Comunicaciones:** Enlace a Configuración > Email (`/configuracion?tab=email`).

---

## 5. Informe pagos (Google Drive, Sheets, OCR, email)

### 5.1 Persistencia y API

- **Tabla:** `configuracion`, clave `informe_pagos_config`.
- **Endpoints:** `GET/PUT /api/v1/configuracion/informe-pagos/configuracion`.
- **Archivo:** `backend/app/api/v1/endpoints/configuracion_informe_pagos.py`.

### 5.2 Holder y sincronización

- **Holder:** `backend/app/core/informe_pagos_config_holder.py`.
  - `sync_from_db()`: carga desde tabla `configuracion` (clave `informe_pagos_config`).
  - Funciones: `get_google_drive_folder_id()`, `get_google_credentials_json()`, `get_google_sheets_id()`, `get_destinatarios_informe_emails()`, `get_horarios_envio()`.

### 5.3 Servicios que usan Informe pagos

| Servicio | ¿Sync antes de usar? | Uso |
|----------|----------------------|-----|
| `services/google_drive_service.upload_image_and_get_link` | ✅ `sync_from_db()` al inicio | Subida de imagen papeleta a Drive. |
| `services/ocr_service.extract_from_image` | ✅ `sync_from_db()` al inicio | OCR Google Vision. |
| `services/google_sheets_informe_service` | ✅ `sync_from_db()` en `_get_sheets_service()` y en `get_sheet_link_for_period` | Escritura en Sheet y link para email. |
| `core/informe_pagos_email.enviar_informe_pagos_email` | ✅ `informe_sync()` y `email_sync()` al inicio | Destinatarios y link desde informe_pagos; SMTP desde email_config. |

El envío del correo del informe usa **Email (SMTP)** vía `email_config_holder` (sync en `send_email()`), por lo que la integración con Configuración > Email queda cubierta.

### 5.4 Frontend

- **Configuración > Informe pagos:** `InformePagosConfig.tsx` llama GET/PUT `/api/v1/configuracion/informe-pagos/configuracion`.
- **Comunicaciones:** Enlace a Configuración > Informe pagos (`/configuracion?tab=informe-pagos`).

---

## 6. Comunicaciones y enlaces a Configuración

La página **Comunicaciones** (`/pagos/comunicaciones`) está integrada con Configuración de la siguiente forma:

1. **Comprueba WhatsApp:** usa `whatsappConfigService.obtenerConfiguracionWhatsApp()` para mostrar si la configuración WhatsApp está cargada.
2. **Enlaces a Configuración:** enlaces directos a:
   - `/configuracion?tab=whatsapp`
   - `/configuracion?tab=email`
   - `/configuracion?tab=ai`
   - `/configuracion?tab=informe-pagos`

Con ello se garantiza que el usuario pueda abrir AI, WhatsApp, Email e Informe pagos desde Comunicaciones.

---

## 7. Recomendaciones (opcionales)

1. **Email holder tras PUT:** Tras `put_email_configuracion` se podría llamar a `email_config_holder.update_from_api(_email_config_stub)` para que el holder refleje de inmediato la nueva config en el mismo proceso, sin esperar al próximo `sync_from_db()`. No es obligatorio porque `send_email` siempre hace `sync_from_db()`.
2. **Documentar en UI:** En Comunicaciones o en cada pestaña de Configuración, un texto breve tipo: “Los cambios se aplican de inmediato para envíos y para el flujo de cobranza por WhatsApp.”
3. **Tests:** Añadir tests de integración que comprueben: tras PUT en cada config, el servicio correspondiente (envío de email, envío WhatsApp, chat AI) usa los valores guardados (por ejemplo, mockeando BD y verificando que se llama a sync o _load_*_from_db).

---

## 8. Tabla de referencia rápida

| Configuración | Clave BD | Holder / Carga | Servicios que la usan |
|---------------|----------|----------------|------------------------|
| AI | `configuracion_ai` | `_load_ai_config_from_db(db)` en cada request | Chat AI, POST /chat, POST /probar, documentos, calificaciones |
| WhatsApp | `whatsapp_config` | `whatsapp_config_holder.sync_from_db()` + `get_whatsapp_config()` | whatsapp_send, whatsapp_service, webhook |
| Email | `email_config` | `email_config_holder.sync_from_db()` + `get_smtp_config()` | email.send_email, notificar_tickets, informe_pagos_email, notificaciones_tabs, configuracion_email probar |
| Informe pagos | `informe_pagos_config` | `informe_pagos_config_holder.sync_from_db()` | google_drive_service, ocr_service, google_sheets_informe_service, informe_pagos_email (destinatarios + link); SMTP vía email_config |

---

**Auditoría realizada.** No se han detectado huecos en la integración Configuración ↔ Servicios para AI, WhatsApp y Email; los servicios que requieren estas configuraciones cargan desde BD (o holder sincronizado con BD) antes de usarlas.
