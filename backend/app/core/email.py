"""
Envío de correo para notificaciones (tickets, etc.).
Usa SMTP desde email_config_holder (configuración del dashboard) o desde settings (.env).
"""
import logging
from typing import List, Optional

from app.core.email_config_holder import get_smtp_config, get_tickets_notify_emails, sync_from_db

logger = logging.getLogger(__name__)


def send_email(
    to_emails: List[str],
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
) -> bool:
    """
    Envía un correo vía SMTP (desde el email configurado en Configuración > Email o .env).
    Antes de enviar sincroniza el holder con la BD para que Notificaciones/CRM usen la config guardada.
    to_emails: lista de direcciones destino.
    Devuelve True si se envió, False si no hay SMTP configurado o falló.
    """
    if not to_emails:
        return False
    sync_from_db()
    cfg = get_smtp_config()
    if not all([cfg.get("smtp_host"), cfg.get("smtp_user"), cfg.get("smtp_password")]):
        logger.warning("SMTP no configurado (SMTP_HOST/USER/PASSWORD). No se envía correo.")
        return False

    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = cfg.get("from_email") or cfg.get("smtp_user")
        msg["To"] = ", ".join(to_emails)

        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        if body_html:
            msg.attach(MIMEText(body_html, "html", "utf-8"))

        port = int(cfg.get("smtp_port") or 587)
        with smtplib.SMTP(cfg["smtp_host"], port) as server:
            server.starttls()
            server.login(cfg["smtp_user"], cfg["smtp_password"])
            server.sendmail(msg["From"], to_emails, msg.as_string())
        logger.info("Correo enviado a %s: %s", to_emails, subject)
        return True
    except Exception as e:
        logger.exception("Error enviando correo: %s", e)
        return False


def notify_ticket_created(ticket_id: int, titulo: str, descripcion: str, cliente_nombre: Optional[str], prioridad: str) -> bool:
    """Notifica por correo que se creó un ticket. Destino: contactos prestablecidos (Configuración > Email o TICKETS_NOTIFY_EMAIL)."""
    to_list = get_tickets_notify_emails()
    if not to_list:
        logger.warning("No hay contactos para notificación de tickets. Configura 'Emails para notificación de tickets' en Configuración > Email o TICKETS_NOTIFY_EMAIL.")
        return False
    subject = f"[CRM] Nuevo ticket #{ticket_id}: {titulo[:50]}"
    body = "Se ha creado un nuevo ticket en el CRM.\n\n"
    body += f"ID: {ticket_id}\nTítulo: {titulo}\nPrioridad: {prioridad}\n"
    if cliente_nombre:
        body += f"Cliente: {cliente_nombre}\n"
    body += f"\nDescripción:\n{descripcion}\n"
    return send_email(to_list, subject, body)


def notify_ticket_updated(ticket_id: int, titulo: str, estado: str, prioridad: str) -> bool:
    """Notifica por correo que se actualizó un ticket. Destino: contactos prestablecidos."""
    to_list = get_tickets_notify_emails()
    if not to_list:
        return False
    subject = f"[CRM] Ticket #{ticket_id} actualizado: {estado}"
    body = f"Ticket #{ticket_id}: {titulo}\nEstado: {estado}\nPrioridad: {prioridad}\n"
    return send_email(to_list, subject, body)
