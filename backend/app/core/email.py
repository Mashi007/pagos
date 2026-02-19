"""
Envío de correo para notificaciones (tickets, etc.).
Usa SMTP desde email_config_holder (configuración del dashboard) o desde settings (.env).
Soporta adjuntos (ej. informe PDF de ticket).
"""
import logging
from typing import List, Optional, Tuple

# Timeout para conexión y envío SMTP (evita 502 por proxy cuando Gmail/red tardan)
SMTP_TIMEOUT_SECONDS = 25

from app.core.email_config_holder import get_smtp_config, get_tickets_notify_emails, get_modo_pruebas_email, sync_from_db

logger = logging.getLogger(__name__)

# Tipo para adjuntos: (nombre_archivo, contenido_bytes)
AttachmentType = Tuple[str, bytes]


def _sanitize_smtp_error(exc: Exception) -> str:
    """Mensaje seguro para mostrar al usuario (sin contraseñas ni rutas)."""
    msg = str(exc).strip()
    if not msg:
        return "Error de conexión SMTP."
    # Mensajes típicos de Gmail/Google que ayudan al usuario
    lower = msg.lower()
    if "username and password not accepted" in lower or "authentication failed" in lower:
        return "Usuario o contraseña no aceptados. Usa una Contraseña de aplicación (App Password) de Gmail."
    if "connection refused" in lower or "timed out" in lower or "timeout" in lower:
        return "La conexión al servidor SMTP tardó demasiado o fue rechazada. Revisa host, puerto (587) y que el servidor no esté en suspensión (Render). Vuelve a intentar."
    if "ssl" in lower or "certificate" in lower:
        return "Error SSL/TLS. Prueba puerto 587 con STARTTLS o 465 con SSL."
    # Limitar longitud y quitar posibles rutas internas
    return msg[:300] if len(msg) <= 300 else msg[:297] + "..."


def send_email(
    to_emails: List[str],
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
    cc_emails: Optional[List[str]] = None,
    bcc_emails: Optional[List[str]] = None,
    attachments: Optional[List[AttachmentType]] = None,
    *,
    respetar_destinos_manuales: bool = False,
) -> Tuple[bool, Optional[str]]:
    """
    Envía un correo vía SMTP (desde el email configurado en Configuración > Email o .env).
    Antes de enviar sincroniza el holder con la BD.
    cc_emails: copia visible (CC). bcc_emails: copia oculta (CCO/BCC).
    attachments: lista de (nombre_archivo, contenido_bytes) para adjuntar (ej. PDF).
    respetar_destinos_manuales: si True, NO redirige a email_pruebas; envía a los correos indicados (para "Enviar Email de Prueba").
    Devuelve (True, None) si se envió; (False, mensaje_error) si no hay SMTP configurado o falló.
    """
    if not to_emails:
        return False, "No hay destinatarios."
    sync_from_db()
    # Modo Pruebas: redirigir todos los envíos al correo(s) de pruebas (desde notificaciones_envios o email_config)
    # EXCEPCIÓN: si respetar_destinos_manuales=True (ej. usuario hizo clic en "Enviar Email de Prueba"), se envían a los correos indicados en la interfaz.
    modo_pruebas, emails_pruebas_list = get_modo_pruebas_email()
    if modo_pruebas and emails_pruebas_list and not respetar_destinos_manuales:
        to_emails = emails_pruebas_list
        cc_list = []
        bcc_list = []
        logger.info("Modo Pruebas: envío redirigido a %s", emails_pruebas_list)
    else:
        if modo_pruebas and not emails_pruebas_list:
            logger.warning("Modo Pruebas activo pero no hay correo de pruebas configurado. Configure en Notificaciones > Configuración o Configuración > Email.")
            return False, "En modo Pruebas debe configurar el correo de pruebas en Notificaciones > Configuración o Configuración > Email."
        cc_list = [e.strip() for e in (cc_emails or []) if e and isinstance(e, str) and "@" in e.strip()]
        bcc_list = [e.strip() for e in (bcc_emails or []) if e and isinstance(e, str) and "@" in e.strip()]
    has_attachments = bool(attachments)
    cfg = get_smtp_config()

    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from email.mime.base import MIMEBase
        from email import encoders

        msg = MIMEMultipart("mixed" if has_attachments else "alternative")
        msg["Subject"] = subject
        msg["From"] = cfg.get("from_email") or cfg.get("smtp_user")
        msg["To"] = ", ".join(to_emails)
        if cc_list:
            msg["Cc"] = ", ".join(cc_list)
        if bcc_list:
            msg["Bcc"] = ", ".join(bcc_list)

        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        if body_html:
            msg.attach(MIMEText(body_html, "html", "utf-8"))

        if has_attachments:
            for filename, content in attachments:
                if not filename or content is None:
                    continue
                part = MIMEBase("application", "octet-stream")
                part.set_payload(content)
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", "attachment", filename=filename)
                msg.attach(part)

        port = int(cfg.get("smtp_port") or 587)
        all_recipients = to_emails + cc_list + bcc_list
        use_tls = (cfg.get("smtp_use_tls") or "true").lower() == "true"
        if port == 465:
            with smtplib.SMTP_SSL(cfg["smtp_host"], port, timeout=SMTP_TIMEOUT_SECONDS) as server:
                server.login(cfg["smtp_user"], cfg["smtp_password"])
                server.sendmail(msg["From"], all_recipients, msg.as_string())
        else:
            with smtplib.SMTP(cfg["smtp_host"], port, timeout=SMTP_TIMEOUT_SECONDS) as server:
                if use_tls:
                    server.starttls()
                server.login(cfg["smtp_user"], cfg["smtp_password"])
                server.sendmail(msg["From"], all_recipients, msg.as_string())
        logger.info("Correo enviado a %s: %s", to_emails, subject)
        return True, None
    except Exception as e:
        logger.exception("Error enviando correo: %s", e)
        return False, _sanitize_smtp_error(e)


def notify_ticket_created(
    ticket_id: int,
    titulo: str,
    descripcion: str,
    cliente_nombre: Optional[str],
    prioridad: str,
    estado: str = "abierto",
    tipo: str = "consulta",
    fecha_creacion=None,
) -> bool:
    """
    Notifica por correo que se creó un ticket y adjunta informe en PDF.
    Destino: contactos configurados en Configuración > Email (Contactos para notificación de tickets).
    Remitente: el email configurado por defecto (SMTP/remitente).
    """
    sync_from_db()
    to_list = get_tickets_notify_emails()
    if not to_list:
        logger.warning(
            "No hay contactos para notificación de tickets. Configura 'Contactos para notificación de tickets' en Configuración > Email."
        )
        return False
    subject = f"[CRM] Nuevo ticket #{ticket_id}: {(titulo or '')[:50]}"
    body = "Se ha creado un nuevo ticket en el CRM.\n\n"
    body += f"ID: {ticket_id}\nTítulo: {titulo}\nPrioridad: {prioridad}\n"
    if cliente_nombre:
        body += f"Cliente: {cliente_nombre}\n"
    body += "\nDescripción:\n" + (descripcion or "") + "\n\n"
    body += "Se adjunta el informe en PDF de este ticket.\n"

    attachments: List[AttachmentType] = []
    try:
        from app.core.ticket_pdf import generar_informe_pdf_ticket

        pdf_bytes = generar_informe_pdf_ticket(
            ticket_id=ticket_id,
            titulo=titulo or "",
            descripcion=descripcion or "",
            cliente_nombre=cliente_nombre,
            prioridad=prioridad or "media",
            estado=estado or "abierto",
            tipo=tipo or "consulta",
            fecha_creacion=fecha_creacion,
        )
        attachments.append((f"informe_ticket_{ticket_id}.pdf", pdf_bytes))
    except Exception as e:
        logger.exception("Error generando PDF del ticket %s: %s", ticket_id, e)
        body += "\n(No se pudo adjuntar el informe PDF.)\n"

    ok, _ = send_email(to_list, subject, body, attachments=attachments if attachments else None)
    return ok


def notify_ticket_updated(ticket_id: int, titulo: str, estado: str, prioridad: str) -> bool:
    """Notifica por correo que se actualizó un ticket. Destino: contactos prestablecidos."""
    to_list = get_tickets_notify_emails()
    if not to_list:
        return False
    subject = f"[CRM] Ticket #{ticket_id} actualizado: {estado}"
    body = f"Ticket #{ticket_id}: {titulo}\nEstado: {estado}\nPrioridad: {prioridad}\n"
    ok, _ = send_email(to_list, subject, body)
    return ok
