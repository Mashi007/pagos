# Auditoría integral: CRM Tickets y Comunicaciones

**Ruta:** `/pagos/crm/tickets` (frontend) — **API:** `GET/POST/PUT /api/v1/tickets`  
**Fecha:** 2025-02-05

## 1. Resumen

- **Tickets** están conectados a la BD (tabla `tickets`, relación con `clientes`).
- **Comunicaciones:** cada ticket puede vincularse a una conversación de WhatsApp (`conversacion_whatsapp_id`) y/o a una comunicación por email (`comunicacion_email_id`). Desde la UI de tickets se puede ir a Comunicaciones cuando el ticket tiene conversación WhatsApp.
- **Email automático al crear ticket:** cada vez que se crea un ticket se envía un correo a los contactos configurados, **con un informe en PDF adjunto**. El remitente es el email configurado por defecto (Configuración > Email). El destino se configura en el mismo apartado: **Contactos para notificación de tickets**.

## 2. Conexión con Comunicaciones

| Aspecto | Detalle |
|--------|---------|
| **Modelo** | `Ticket` tiene `conversacion_whatsapp_id` y `comunicacion_email_id` (nullable). |
| **Frontend** | En `TicketsAtencion.tsx`, si el ticket tiene `conversacion_whatsapp_id`, se muestra un botón "Ver conversación" que navega a `/comunicaciones?conversacion_id={id}`. |
| **Creación** | Al crear/editar ticket se pueden enviar `conversacion_whatsapp_id` y `comunicacion_email_id` en el payload (schemas `TicketCreate` / `TicketUpdate`). |
| **API Comunicaciones** | Endpoints de comunicaciones y conversaciones WhatsApp están en `comunicaciones.py`; la página Comunicaciones usa `conversacion_id` para cargar el hilo. |

La conexión es correcta: desde un ticket con conversación WhatsApp se puede ir directo a Comunicaciones.

## 3. Flujo de creación de ticket y envío de email con PDF

1. Usuario crea ticket en **CRM → Tickets** (formulario Nuevo Ticket).
2. Frontend llama `POST /api/v1/tickets` con `TicketCreate`.
3. Backend (`tickets.py`): inserta en `tickets`, hace `commit` y `refresh`.
4. Backend llama `notify_ticket_created(...)` en `app/core/email.py`:
   - Obtiene destinatarios de `get_tickets_notify_emails()` (Configuración > Email > Contactos para notificación de tickets, o `TICKETS_NOTIFY_EMAIL` en .env).
   - Genera el informe PDF con `app/core/ticket_pdf.generar_informe_pdf_ticket(...)` (reportlab).
   - Envía un solo correo con cuerpo en texto y **adjunto** `informe_ticket_{id}.pdf`.
5. El **remitente** del correo es el configurado en Configuración > Email (SMTP / Email del remitente).

Si la generación del PDF falla, se envía igual el correo con un aviso en el cuerpo de que no se pudo adjuntar el PDF.

## 4. Configuración del email para tickets

| Dónde | Qué se configura |
|-------|-------------------|
| **Configuración > Email** (dashboard) | **Contactos para notificación de tickets:** uno o varios emails separados por coma. Son los **destinatarios** del correo (y del PDF) cuando se crea un ticket. |
| **Mismo apartado** | **Email del remitente / SMTP:** define **desde qué cuenta** se envía (por defecto). |

- **Destino del informe de ticket:** campo "Contactos para notificación de tickets" en Configuración > Email.  
- **Origen del correo:** el email por defecto ya configurado (remitente SMTP).

No hay pantalla separada solo para “email de tickets”: todo está en **Configuración > Email**, en la sección **Notificación automática de tickets (CRM)**.

## 5. Archivos relevantes

| Componente | Archivo |
|------------|---------|
| API Tickets | `backend/app/api/v1/endpoints/tickets.py` |
| Modelo Ticket | `backend/app/models/ticket.py` |
| Schemas ticket | `backend/app/schemas/ticket.py` |
| Notificación + PDF | `backend/app/core/email.py`, `backend/app/core/ticket_pdf.py` |
| Config email (holder) | `backend/app/core/email_config_holder.py` |
| Config email API | `backend/app/api/v1/endpoints/configuracion_email.py` |
| Página Tickets | `frontend/src/pages/TicketsAtencion.tsx` |
| Config Email UI | `frontend/src/components/configuracion/EmailConfig.tsx` |
| Comunicaciones | `frontend/src/pages/Comunicaciones.tsx`, `frontend/src/components/comunicaciones/Comunicaciones.tsx` |

## 6. Checklist de verificación

- [x] Listado de tickets desde BD con paginación y filtros.
- [x] Crear ticket persiste en BD y dispara notificación por email.
- [x] Al crear ticket se genera informe PDF y se adjunta al correo.
- [x] Destino del correo configurable en Configuración > Email (Contactos para notificación de tickets).
- [x] Remitente = email configurado por defecto (SMTP/remitente).
- [x] Enlace desde ticket con `conversacion_whatsapp_id` a Comunicaciones.
- [x] Modelo Ticket con `conversacion_whatsapp_id` y `comunicacion_email_id` para vínculo con Comunicaciones.
