# Auditoría integral: Configuración de email (Configuración > Email)

**URL de configuración:** `https://rapicredit.onrender.com/pagos/configuracion?tab=email`  
**Backend:** tabla `configuracion`, clave `email_config`. API: `GET/PUT /api/v1/configuracion/email/configuracion`, `POST /api/v1/configuracion/email/probar`, etc.

Esta auditoría verifica que **cualquier módulo que requiera envío de correo** use la configuración guardada en **Configuración > Email**, de forma que un solo punto de configuración rija SMTP, remitente, modo pruebas y contactos en toda la aplicación.

---

## 1. Flujo de la configuración

| Paso | Componente | Descripción |
|------|------------|-------------|
| 1 | Frontend `EmailConfig.tsx` | Usuario edita SMTP, IMAP, contactos tickets, modo pruebas. `PUT /api/v1/configuracion/email/configuracion`. |
| 2 | Backend `configuracion_email.py` | Recibe payload, actualiza stub, llama `update_from_api()` y persiste en tabla `configuracion` (clave `email_config`). |
| 3 | `email_config_holder.py` | Holder en memoria con la config actual. `sync_from_db()` la carga desde BD. |
| 4 | `email.py` | `send_email()` llama `sync_from_db()` y usa `get_smtp_config()` para enviar. Modo pruebas y contactos tickets vía holder. |

**Conclusión:** Toda configuración editable en la pantalla se persiste en BD y se usa en los envíos a través del holder y de `send_email()`.

---

## 2. Módulos que envían correo – Estado de uso de Configuración > Email

| Módulo / funcionalidad | Archivo(s) | ¿Usa config Email? | Detalle |
|------------------------|------------|--------------------|---------|
| **Envío genérico** | `app/core/email.py` → `send_email()` | ✅ Sí | `sync_from_db()` + `get_smtp_config()`. Modo pruebas: `get_modo_pruebas_email()`. |
| **Notificaciones a clientes (recordatorios)** | `notificaciones.py`, `notificaciones_tabs.py` | ✅ Sí | Llaman `send_email()`. SMTP y remitente desde config. |
| **Envío prueba plantilla** | `notificaciones.py` (POST enviar a cliente) | ✅ Sí | `send_email([correo], asunto, cuerpo)`. |
| **Tickets: notificación creación/actualización** | `app/core/email.py` → `notify_ticket_created`, `notify_ticket_updated` | ✅ Sí | Destino: `get_tickets_notify_emails()` (Contactos para notificación de tickets). SMTP desde config. |
| **Tickets: informe REVISAR (WhatsApp)** | `whatsapp_service.py` → `_crear_ticket_informe_revisar` | ✅ Sí | Destino: `get_tickets_notify_emails()`; si vacío, fallback a email por defecto. SMTP desde config. |
| **Informe de pagos (programado)** | `informe_pagos_email.py` | ✅ Sí | Destinatarios desde `informe_pagos_config_holder`; **SMTP** desde `email_config_holder` (`email_sync()` antes de `send_email()`). |
| **Prueba de configuración Email** | `configuracion_email.py` (POST probar) | ✅ Sí | `sync_from_db()` + `send_email()`. |
| **Olvido de contraseña** | `auth.py` → `forgot_password` | ✅ Sí | **Destino:** primero `get_tickets_notify_emails()` (Configuración > Email); si vacío, `.env` `FORGOT_PASSWORD_NOTIFY_EMAIL`; luego fallback. **SMTP:** vía `send_email()`. |

---

## 3. Verificaciones realizadas

### 3.1 Un solo punto de envío

- Todo el envío SMTP pasa por `app/core/email.py` → `send_email()`.
- No hay uso directo de `smtplib` fuera de `email.py`.
- **Correcto:** un solo punto asegura que siempre se use la config del holder (y por tanto la guardada en Configuración > Email o .env).

### 3.2 Sincronización con BD

- `send_email()` llama `sync_from_db()` al inicio.
- `notify_ticket_created` / `notify_ticket_updated` llaman `sync_from_db()` y `get_tickets_notify_emails()`.
- **Correcto:** la config en BD se aplica antes de cada envío, incluso con varios workers (p. ej. Render).

### 3.3 Modo pruebas

- `get_modo_pruebas_email()` lee del holder (y hace `sync_from_db()`).
- Cuando modo pruebas está activo y hay `email_pruebas` configurado, **todos** los envíos se redirigen a ese correo.
- **Correcto:** aplica a cualquier módulo que use `send_email()`.

### 3.4 Destinatarios “de sistema” (tickets, informe REVISAR)

- **Contactos para notificación de tickets:** `tickets_notify_emails` en config Email → `get_tickets_notify_emails()`.
- **Ticket informe REVISAR:** desde la auditoría se cambió a usar `get_tickets_notify_emails()` con fallback a un email por defecto si no hay config.
- **Correcto:** un solo lugar (Configuración > Email) define a quién notificar por tickets e informe REVISAR.

### 3.5 Informe de pagos

- Destinatarios y texto: `informe_pagos_config_holder` (Configuración > Informe pagos).
- SMTP: `email_config_holder` (`email_sync()` en `enviar_informe_pagos_email()`).
- **Correcto:** el envío del informe usa la misma configuración de email que el resto de la app.

---

## 4. Correcciones aplicadas en esta auditoría

1. **`app/core/email.py`**  
   - **Problema:** En `send_email()` se usaba `cfg` sin asignarlo (falta de `cfg = get_smtp_config()`).  
   - **Corrección:** Se añadió `cfg = get_smtp_config()` antes de construir el mensaje y conectar por SMTP.

2. **`app/services/whatsapp_service.py`**  
   - **Problema:** El aviso por “ticket informe REVISAR” enviaba siempre a un email fijo (`EMAIL_TICKET_REVISAR`).  
   - **Corrección:** Se usa `get_tickets_notify_emails()` como destino; si la lista está vacía, se usa el email por defecto. Así el destino se controla desde Configuración > Email (Contactos para notificación de tickets).

---

## 5. Olvido de contraseña

- **Implementación:** El destino del correo de olvido de contraseña usa primero **Contactos para notificación de tickets** (`get_tickets_notify_emails()`); si está vacío, se usa `FORGOT_PASSWORD_NOTIFY_EMAIL` de .env y, si no, el fallback `itmaster@rapicreditca.com`. Así, un solo listado en Configuración > Email puede centralizar notificaciones de tickets, informe REVISAR y avisos de olvido de contraseña.

---

## 6. Resumen

| Aspecto | Estado |
|---------|--------|
| Un solo punto de envío (`send_email`) | ✅ |
| Config persistida en BD y sincronizada antes de enviar | ✅ |
| Modo pruebas aplicado a todos los envíos | ✅ |
| Notificaciones a clientes (recordatorios, plantillas) | ✅ Usan config Email |
| Notificaciones de tickets (creación, actualización, informe REVISAR) | ✅ Usan config Email (contactos + SMTP) |
| Informe de pagos programado | ✅ SMTP desde config Email |
| Prueba de configuración desde la UI | ✅ |
| Olvido de contraseña | ✅ Destino desde config Email (o .env si no hay contactos); SMTP desde config |

**Conclusión:** La configuración guardada en **https://rapicredit.onrender.com/pagos/configuracion?tab=email** se aplica de forma correcta y centralizada a **cualquier módulo que requiera envío de correo**, salvo el destino del correo de olvido de contraseña, que sigue leyéndose de variables de entorno. Las correcciones aplicadas eliminan el bug de `cfg` no definido y alinean el aviso de “ticket informe REVISAR” con la configuración de email.
