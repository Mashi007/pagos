# Auditoría integral: Configuración de WhatsApp (Configuración > WhatsApp)

**URL de configuración:** `https://rapicredit.onrender.com/pagos/configuracion?tab=whatsapp`  
**Backend:** tabla `configuracion`, clave `whatsapp_config`. API: `GET/PUT /api/v1/configuracion/whatsapp/configuracion`, `POST /api/v1/configuracion/whatsapp/probar`, `GET /api/v1/configuracion/whatsapp/test-completo`.

Esta auditoría verifica que **cualquier módulo que requiera envío o recepción por WhatsApp** use la configuración guardada en **Configuración > WhatsApp**, de forma que un solo punto de configuración rija API URL, token, Phone Number ID, webhook y verificación de firma en toda la aplicación.

---

## 1. Flujo de la configuración

| Paso | Componente | Descripción |
|------|------------|-------------|
| 1 | Frontend `WhatsAppConfig.tsx` | Usuario edita API URL, Access Token, Phone Number ID, Business Account ID, Webhook Verify Token, modo pruebas, teléfono de pruebas. `PUT /api/v1/configuracion/whatsapp/configuracion`. |
| 2 | Backend `configuracion_whatsapp.py` | Recibe payload, actualiza stub en memoria, persiste en tabla `configuracion` (clave `whatsapp_config`), llama `whatsapp_sync_from_db()` para actualizar el holder. |
| 3 | `whatsapp_config_holder.py` | Holder en memoria con la config actual. `sync_from_db()` carga desde la tabla `configuracion`. |
| 4 | Módulos que envían/reciben | Llaman `sync_from_db()` y `get_whatsapp_config()` (o `get_webhook_verify_token()`) antes de usar Meta API o verificar webhook. |

**Persistencia:** La configuración (incluido el token) se guarda en BD; no se pierde al reiniciar ni al redesplegar (véase `POLITICAS_CREDENCIALES_GMAIL_WHATSAPP.md`).

**Seguridad:** GET de configuración **nunca** expone `access_token` ni `webhook_verify_token` en texto plano (se devuelve `***`). PUT no sobrescribe el token si el frontend envía `***` o vacío.

---

## 2. Módulos que usan WhatsApp – Estado de uso de Configuración > WhatsApp

| Módulo / funcionalidad | Archivo(s) | ¿Usa config WhatsApp? | Detalle |
|------------------------|------------|------------------------|---------|
| **Envío de texto genérico** | `app/core/whatsapp_send.py` → `send_whatsapp_text()` | ✅ Sí | `whatsapp_sync_from_db()` + `get_whatsapp_config()`. Único punto de envío para mensajes de texto (Meta Cloud API). |
| **Webhook: verificación (GET)** | `whatsapp.py` → `verify_webhook` | ✅ Sí | `whatsapp_sync_from_db()` + `get_webhook_verify_token()` (desde holder/BD o .env). |
| **Webhook: recepción (POST)** | `whatsapp.py` → `receive_webhook` | ✅ Sí | `whatsapp_sync_from_db()` + `get_whatsapp_config()` para firma (app_secret) y procesamiento. |
| **Comunicaciones: enviar mensaje** | `comunicaciones.py` → `enviar_whatsapp` | ✅ Sí | `whatsapp_sync_from_db()` + `get_whatsapp_config()` + `send_whatsapp_text()`. |
| **Notificaciones (tabs)** | `notificaciones_tabs.py` → `_enviar_correos_items` | ✅ Sí | Llama `send_whatsapp_text(telefono, cuerpo)`; esta función usa el holder (sync + get_whatsapp_config). |
| **WhatsApp Service: mensajes entrantes** | `whatsapp_service.py` → `_send_whatsapp_async` | ✅ Sí | `whatsapp_sync_from_db()` + `get_whatsapp_config()` antes de cada envío a Meta. |
| **WhatsApp Service: descarga de medios (OCR)** | `whatsapp_service.py` (procesamiento de imagen) | ✅ Sí | `whatsapp_sync_from_db()` + `get_whatsapp_config()` para token y api_url (descarga de imagen desde Meta). |
| **Configuración: probar envío** | `configuracion_whatsapp.py` → `post_whatsapp_probar` | ✅ Sí | Carga stub desde BD; destino según modo_pruebas/telefono_pruebas; envío vía `send_whatsapp_text()` (que usa holder ya sincronizado tras PUT). |
| **Configuración: test completo** | `configuracion_whatsapp.py` → `get_whatsapp_test_completo` | ✅ Sí | Lee stub (cargado desde BD); usa api_url, access_token, phone_number_id para probar conexión con Meta API. |

---

## 3. Verificaciones realizadas

### 3.1 Un solo punto de envío de mensajes de texto

- Todo el envío de mensajes de texto por WhatsApp pasa por `app/core/whatsapp_send.py` → `send_whatsapp_text()`.
- No hay llamadas directas a la API de Meta para “enviar mensaje” fuera de `whatsapp_send.py` y de `whatsapp_service._send_whatsapp_async` (que usa la misma config vía `get_whatsapp_config()`).
- **Correcto:** un solo punto de envío asegura que siempre se use la config del holder (guardada en Configuración > WhatsApp o .env).

### 3.2 Sincronización con BD

- Los módulos que envían o reciben llaman `whatsapp_sync_from_db()` antes de usar la config (o llaman a `send_whatsapp_text()` / `get_whatsapp_config()`, que internamente sincronizan).
- Tras `PUT /configuracion/whatsapp/configuracion` se llama `whatsapp_sync_from_db()` para que el holder refleje de inmediato lo guardado en BD.
- **Correcto:** la config en BD se aplica antes de cada uso, incluso con varios workers (p. ej. Render).

### 3.3 Webhook (verificación y recepción)

- **Verificación (GET):** usa `get_webhook_verify_token()`, que lee del holder (y por tanto de BD o .env).
- **Recepción (POST):** usa `get_whatsapp_config()` para `app_secret` (verificación de firma X-Hub-Signature-256) y el procesamiento de mensajes usa el mismo servicio que envía con la config del holder.
- **Correcto:** el webhook depende íntegramente de la configuración central.

### 3.4 Descarga de medios (imágenes para OCR)

- En el flujo de imagen por WhatsApp (pagos_whatsapp, digitalización), se usa `get_whatsapp_config()` para token y api_url y se descarga la imagen desde la API de Meta.
- **Correcto:** no hay credenciales hardcodeadas; todo sale del holder/BD.

### 3.5 Modo pruebas y teléfono de pruebas

- **Modo pruebas / teléfono de pruebas** se usan solo en **Configuración > WhatsApp > Probar**: para elegir el destino del mensaje de prueba (teléfono indicado en el body o, en modo pruebas, `telefono_pruebas`).
- No existe un “modo pruebas” global que redirija **todos** los envíos de WhatsApp a un solo número (a diferencia del email). Los envíos reales (notificaciones, comunicaciones, respuestas del bot) van siempre al destinatario correspondiente.
- **Correcto:** comportamiento esperado; la configuración de prueba solo afecta al botón “Probar” en la pantalla.

---

## 4. Consistencia holder vs API (stub)

- **API** (`configuracion_whatsapp.py`): mantiene un stub en memoria, lo persiste en BD y, tras PUT, llama `whatsapp_sync_from_db()` para actualizar el holder.
- **Holder** (`whatsapp_config_holder.py`): expone `get_whatsapp_config()` y `get_webhook_verify_token()`; se alimenta con `sync_from_db()` desde la tabla `configuracion`.
- **Claves en BD/stub (API):** api_url, access_token, phone_number_id, business_account_id, webhook_verify_token, modo_pruebas, telefono_pruebas.
- **Claves en holder:** api_url, access_token, phone_number_id, business_account_id, webhook_verify_token, **app_secret** (no persistido por la API actual; el holder lo toma de `_default_config()` → settings/.env).

**Conclusión:** Para envío y verificación de webhook (verify_token) la configuración es única y correcta. El **App Secret** (firma del webhook) se usa en `whatsapp.py` vía `get_whatsapp_config()` y hoy solo puede configurarse por **variables de entorno** (`.env`), no desde la pantalla Configuración > WhatsApp.

---

## 5. Recomendaciones opcionales

1. **App Secret en la UI:** Si se desea que el App Secret sea configurable desde la pantalla (y persistido en BD como el token), se puede añadir el campo en el modelo/schema de configuración WhatsApp, en el stub, en el holder (`update_from_api` y `sync_from_db`) y en el frontend, manteniendo la misma política de no exponerlo en GET (devolver `***`).
2. **Modo pruebas global (redirigir todos los envíos):** Si en el futuro se requiere un “modo pruebas” que envíe todos los mensajes de WhatsApp a un solo número (análogo al email), habría que leer `modo_pruebas` y `telefono_pruebas` del holder (persistiéndolos desde el stub actual) y aplicar la redirección en `send_whatsapp_text()` o en el punto único de envío.

---

## 6. Resumen

| Aspecto | Estado |
|---------|--------|
| Un solo punto de envío de texto (`send_whatsapp_text`) | ✅ |
| Config persistida en BD y sincronizada antes de usar | ✅ |
| Webhook (verificación y recepción) usa config central | ✅ |
| Comunicaciones (enviar WhatsApp) | ✅ Usan config WhatsApp |
| Notificaciones (tabs) envío WhatsApp | ✅ Usan config WhatsApp |
| WhatsApp Service (respuestas, descarga medios) | ✅ Usan config WhatsApp |
| Prueba y test completo desde la UI | ✅ |
| App Secret (firma webhook) | ⚠️ Solo desde .env; no editable en Configuración > WhatsApp |

**Conclusión:** La configuración guardada en **https://rapicredit.onrender.com/pagos/configuracion?tab=whatsapp** se aplica de forma correcta y centralizada a **cualquier módulo que requiera envío o recepción por WhatsApp** (webhook, comunicaciones, notificaciones, digitalización por imagen). La única excepción es el **App Secret** para la firma del webhook, que actualmente solo se configura por variables de entorno.
