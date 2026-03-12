# Verificación: email con camino único de configuración

**Objetivo:** Toda la configuración de correo (SMTP, IMAP, contactos para notificaciones) tiene un **único punto de entrada**: la pantalla **Configuración > Email** (`/pagos/configuracion?tab=email` en [RapiCredit](https://rapicredit.onrender.com/pagos/configuracion?tab=email)).

---

## 1. Único lugar donde se escribe la configuración de email

| Capa | Dónde | Qué |
|------|--------|-----|
| **Frontend** | Página Configuración, pestaña Email | Formulario que llama a `PUT /api/v1/configuracion/email/configuracion`. No hay otra pantalla que guarde SMTP/IMAP/contactos. |
| **Backend** | `configuracion_email.py` | Único endpoint que escribe en la tabla `configuracion` con clave `email_config`: **PUT** `/api/v1/configuracion/email/configuracion`. |
| **BD** | Tabla `configuracion`, clave `email_config` | Un solo registro JSON con la config (SMTP, IMAP, tickets_notify_emails, modo_pruebas, etc.). |

No existe otro endpoint ni pantalla que modifique `email_config` en BD.

---

## 2. Cómo se lee la configuración (todo pasa por el holder)

Todo el sistema que envía correo o necesita datos de email usa **`app.core.email_config_holder`**, que **siempre** obtiene los datos desde BD (tabla `configuracion`, clave `email_config`) vía `sync_from_db()`:

| Consumidor | Uso | Origen efectivo |
|------------|-----|------------------|
| **email.send_email()** | Envío SMTP (prueba, tickets, notificaciones, olvido contraseña, informe pagos) | `get_smtp_config()` → `sync_from_db()` → `_current` (rellenado desde BD). Si no hay nada en BD, fallback a `settings` (.env). |
| **email_config_holder.get_tickets_notify_emails()** | Destinatarios notificación tickets; destino olvido contraseña (auth) | `_current["tickets_notify_emails"]` (cargado por `sync_from_db()`). Fallback a `settings.TICKETS_NOTIFY_EMAIL`. |
| **email_config_holder.get_modo_pruebas_email()** | Redirigir envíos a email de pruebas | `sync_from_db()` + `_current` / notificaciones_envios. |
| **configuracion_email (GET/PUT/estado/probar/probar-imap)** | API de la pestaña Email | Lee/escribe en stub que se persiste en BD como `email_config`; POST probar usa `get_smtp_config()` (misma fuente). |
| **informe_pagos_email** | Envío de informe de pagos por correo | `send_email()` → mismo flujo centralizado. |
| **auth (forgot-password)** | Envío de correo al solicitar restablecer contraseña | `get_tickets_notify_emails()` para destino; `send_email()` para envío. |

Ningún módulo usa directamente `settings.SMTP_*` para enviar; solo el holder, y solo como **fallback** cuando en BD no hay `smtp_user` (nadie ha guardado desde la UI).

---

## 3. Flujo resumido

```
Usuario edita en:  /pagos/configuracion?tab=email
        ↓
Frontend: PUT /api/v1/configuracion/email/configuracion
        ↓
Backend: configuracion_email.put_email_configuracion()
        → actualiza _email_config_stub
        → update_from_api(stub) → holder _current
        → _persist_email_config(db) → tabla configuracion, clave "email_config"
        ↓
Cualquier envío o lectura de config:
        → sync_from_db() lee de BD y actualiza _current
        → get_smtp_config() / get_tickets_notify_emails() / get_modo_pruebas_email()
        → usan _current (origen: BD guardada desde la pestaña Email)
```

---

## 4. Variables .env (solo respaldo)

En `app.core.config` existen opcionales: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `TICKETS_NOTIFY_EMAIL`.  
Se usan **únicamente** cuando:

- No hay registro `email_config` en BD, o  
- Hay registro pero sin `smtp_user` (config no guardada desde la UI).

Para que el sistema use **solo** lo configurado en la pantalla, basta con guardar una vez la configuración desde **Configuración > Email**; a partir de ahí la fuente de verdad es la BD.

---

## 5. Conclusión

- **Camino único de configuración:** `/pagos/configuracion?tab=email` → PUT `/api/v1/configuracion/email/configuracion` → BD `configuracion.email_config`.
- **Camino único de lectura para envíos:** `sync_from_db()` → `_current` → `get_smtp_config()` / `get_tickets_notify_emails()` / `get_modo_pruebas_email()`.
- No hay otros endpoints ni pantallas que escriban la config de email; el sistema está centralizado y bien configurado con la pestaña Email como único punto de entrada.
