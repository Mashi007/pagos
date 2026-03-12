"""
Env�o de correo para notificaciones (tickets, etc.).
Usa SMTP desde email_config_holder (configuraci�n del dashboard) o desde settings (.env).
Soporta adjuntos (ej. informe PDF de ticket).
Tambi�n soporta prueba de conexi�n IMAP para recibir correos.
"""
import logging
import time
from typing import List, Optional, Tuple

# Timeout para conexi�n y env�o SMTP/IMAP (evita 502 por proxy cuando Gmail/red tardan)
SMTP_TIMEOUT_SECONDS = 25
IMAP_TIMEOUT_SECONDS = 25

from app.core.email_config_holder import get_smtp_config, get_tickets_notify_emails, get_modo_pruebas_email, sync_from_db

logger = logging.getLogger(__name__)

# Tipo para adjuntos: (nombre_archivo, contenido_bytes)
AttachmentType = Tuple[str, bytes]


def _sanitize_imap_error(exc: Exception) -> str:
    """Mensaje seguro para mostrar al usuario al fallar conexi�n IMAP (sin contrase�as ni rutas)."""
    msg = str(exc).strip()
    # Si el mensaje es repr de bytes (b'...'), extraer texto para no mostrar b'...' en la UI
    if msg.startswith("b'") and msg.endswith("'"):
        try:
            msg = msg[2:-1].encode().decode('unicode_escape')
        except Exception:
            msg = msg[2:-1]
    if not msg:
        return "Error de conexi�n IMAP."
    lower = msg.lower()
    if "username and password not accepted" in lower or "authentication failed" in lower or "login failed" in lower:
        return "Usuario o contrase�a no aceptados. Gmail personal: usa Contrase�a de aplicaci�n. Cuentas corporativas/Google Workspace: prueba con tu contrase�a normal."
    if "network is unreachable" in lower or "errno 101" in lower or "enetunreach" in lower:
        return "La red del servidor no puede alcanzar IMAP (ej. en Render las conexiones salientes pueden estar bloqueadas). Prueba desde tu red local o verifica restricciones de red del proveedor."
    if "connection refused" in lower or "timed out" in lower or "timeout" in lower:
        return "La conexi�n al servidor IMAP tard� demasiado o fue rechazada. Revisa host, puerto (993 o 143) y que el servidor no est� en suspensi�n."
    if "ssl" in lower or "certificate" in lower:
        return "Error SSL/TLS. Prueba puerto 993 con SSL o 143 con STARTTLS."
    if "authenticationfailed" in lower or "invalid credentials" in lower:
        return "Usuario o contrase�a no aceptados. Gmail personal: usa Contrase�a de aplicaci�n. Cuentas corporativas/Google Workspace: prueba con tu contrase�a normal."
    return msg[:300] if len(msg) <= 300 else msg[:297] + "..."



def _sanitize_smtp_error(exc: Exception) -> str:
    """Mensaje seguro para el usuario al fallar SMTP (sin contrase�as ni rutas)."""
    msg = str(exc).strip()
    if not msg:
        return "Error de conexi�n SMTP."
    lower = msg.lower()
    if "username and password not accepted" in lower or "authentication failed" in lower or "login failed" in lower:
        return "Usuario o contrase�a no aceptados. Gmail personal: usa Contrase�a de aplicaci�n. Cuentas corporativas/Google Workspace: prueba con tu contrase�a normal."
    if "connection refused" in lower or "timed out" in lower or "timeout" in lower:
        return "La conexi�n al servidor SMTP tard� demasiado o fue rechazada. Revisa host, puerto (587 o 465) y red."
    if "ssl" in lower or "certificate" in lower:
        return "Error SSL/TLS. Prueba puerto 587 con TLS o 465 con SSL."
    if "connection unexpectedly closed" in lower or "connection closed" in lower or "serverdisconnected" in lower:
        return "El servidor SMTP cerro la conexion durante el inicio de sesion. En entornos cloud (Render, etc.) suele deberse a restricciones de red o a que Gmail exige Contrasena de aplicacion; revisa puerto (587 o 465) y vuelve a intentar."
    return msg[:300] if len(msg) <= 300 else msg[:297] + "..."

def test_imap_connection(
    imap_host: str,
    imap_port: int,
    imap_user: str,
    imap_password: str,
    imap_use_ssl: bool = True,
) -> Tuple[bool, Optional[str], Optional[List[str]]]:
    """
    Prueba la conexi�n IMAP y devuelve informaci�n sobre carpetas disponibles.
    Retorna: (�xito, mensaje_error, lista_de_carpetas)
    - �xito: True si la conexi�n fue exitosa
    - mensaje_error: Descripci�n legible del error (None si no hay error)
    - lista_de_carpetas: Lista de nombres de carpetas (None si fall�)
    """
    try:
        import imaplib

        logger.info("IMAP fase 1/4: conectando a %s:%s (SSL=%s, timeout=%ss)", imap_host, imap_port, imap_use_ssl, IMAP_TIMEOUT_SECONDS)
        if imap_use_ssl:
            server = imaplib.IMAP4_SSL(imap_host, imap_port, timeout=IMAP_TIMEOUT_SECONDS)
        else:
            server = imaplib.IMAP4(imap_host, imap_port, timeout=IMAP_TIMEOUT_SECONDS)
            server.starttls()
        logger.info("IMAP fase 2/4: conexion TCP establecida, enviando LOGIN para %s", imap_user)

        server.login(imap_user, imap_password)
        
        logger.info("IMAP fase 3/4: LOGIN OK, listando carpetas")

        # Listar carpetas disponibles
        _, mailboxes = server.list()
        logger.info("IMAP fase 4/4: LIST OK, %d entradas", len(mailboxes) if mailboxes else 0)
        folder_list = []
        for mailbox in mailboxes:
            try:
                # Parsear respuesta de IMAP: (\HasNoChildren) "/" "INBOX"
                parts = mailbox.decode("utf-8").split('" "')
                if len(parts) >= 2:
                    folder_name = parts[-1].strip('"')
                    folder_list.append(folder_name)
            except Exception:
                pass

        server.close()
        server.logout()

        msg = f"Conexi�n IMAP exitosa. Se encontraron {len(folder_list)} carpeta(s): {', '.join(folder_list[:5])}"
        if len(folder_list) > 5:
            msg += f" y {len(folder_list) - 5} m�s."
        
        logger.info("Prueba IMAP exitosa para %s: %d carpetas", imap_user, len(folder_list))
        return True, None, folder_list

    except Exception as e:
        logger.exception("Error probando IMAP %s:%s para usuario %s", imap_host, imap_port, imap_user)
        error_msg = _sanitize_imap_error(e)
        return False, error_msg, None


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
    Env�a un correo v�a SMTP (desde el email configurado en Configuraci�n > Email o .env).
    Antes de enviar sincroniza el holder con la BD.
    cc_emails: copia visible (CC). bcc_emails: copia oculta (CCO/BCC).
    attachments: lista de (nombre_archivo, contenido_bytes) para adjuntar (ej. PDF).
    respetar_destinos_manuales: si True, NO redirige a email_pruebas; env�a a los correos indicados (para "Enviar Email de Prueba").
    Devuelve (True, None) si se envi�; (False, mensaje_error) si no hay SMTP configurado o fall�.
    """
    if not to_emails:
        return False, "No hay destinatarios."
    sync_from_db()
    # Modo Pruebas: redirigir todos los env�os al correo(s) de pruebas (desde notificaciones_envios o email_config)
    # EXCEPCI�N: si respetar_destinos_manuales=True (ej. usuario hizo clic en "Enviar Email de Prueba"), se env�an a los correos indicados en la interfaz.
    modo_pruebas, emails_pruebas_list = get_modo_pruebas_email()
    if modo_pruebas and emails_pruebas_list and not respetar_destinos_manuales:
        to_emails = emails_pruebas_list
        cc_list = []
        bcc_list = []
        logger.info("Modo Pruebas: env�o redirigido a %s", emails_pruebas_list)
    else:
        if modo_pruebas and not emails_pruebas_list:
            logger.warning("Modo Pruebas activo pero no hay correo de pruebas configurado. Configure en Notificaciones > Configuraci�n o Configuraci�n > Email.")
            return False, "En modo Pruebas debe configurar el correo de pruebas en Notificaciones > Configuraci�n o Configuraci�n > Email."
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
    Notifica por correo que se cre� un ticket y adjunta informe en PDF.
    Destino: contactos configurados en Configuraci�n > Email (Contactos para notificaci�n de tickets).
    Remitente: el email configurado por defecto (SMTP/remitente).
    """
    sync_from_db()
    to_list = get_tickets_notify_emails()
    if not to_list:
        logger.warning(
            "No hay contactos para notificaci�n de tickets. Configura 'Contactos para notificaci�n de tickets' en Configuraci�n > Email."
        )
        return False
    subject = f"[CRM] Nuevo ticket #{ticket_id}: {(titulo or '')[:50]}"
    body = "Se ha creado un nuevo ticket en el CRM.\n\n"
    body += f"ID: {ticket_id}\nT�tulo: {titulo}\nPrioridad: {prioridad}\n"
    if cliente_nombre:
        body += f"Cliente: {cliente_nombre}\n"
    body += "\nDescripci�n:\n" + (descripcion or "") + "\n\n"
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
    """Notifica por correo que se actualiz� un ticket. Destino: contactos prestablecidos."""
    to_list = get_tickets_notify_emails()
    if not to_list:
        return False
    subject = f"[CRM] Ticket #{ticket_id} actualizado: {estado}"
    body = f"Ticket #{ticket_id}: {titulo}\nEstado: {estado}\nPrioridad: {prioridad}\n"
    ok, _ = send_email(to_list, subject, body)
    return ok
