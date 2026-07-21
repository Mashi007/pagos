"""
Env�o de correo para notificaciones (tickets, etc.).
Usa SMTP desde email_config_holder (configuraci�n del dashboard) o desde settings (.env).
Soporta adjuntos (ej. informe PDF de ticket).
Tambi�n soporta prueba de conexi�n IMAP para recibir correos.
"""
import logging
import re
import smtplib
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from email.utils import formatdate

# Timeout para conexion y envio SMTP/IMAP (evita 502 por proxy cuando Gmail/red tardan)
SMTP_TIMEOUT_SECONDS = 25
IMAP_TIMEOUT_SECONDS = 25
# Gmail en lotes grandes: cierra el login tras muchos connect+auth seguidos.
SMTP_SEND_MAX_ATTEMPTS = 4
SMTP_RETRY_BASE_SECONDS = 2.5

from app.core.email_config_holder import (
    get_smtp_config,
    get_tickets_notify_emails,
    get_modo_pruebas_email,
    get_recibos_bcc_emails,
    sync_from_db,
)
from app.core.config import settings
from app.core.email_phases import (
    FASE_IMAP_COMPLETA,
    FASE_IMAP_CONEXION,
    FASE_IMAP_LIST,
    FASE_IMAP_LOGIN,
    FASE_MODO_PRUEBAS,
    FASE_SMTP_CONFIG,
    FASE_SMTP_CONEXION,
    FASE_SMTP_ENVIO,
    log_phase,
)

logger = logging.getLogger(__name__)

# Tipo para adjuntos: (nombre_archivo, contenido_bytes)
AttachmentType = Tuple[str, bytes]


def mask_email_for_log(addr: str) -> str:
    """Oculta parte del local-part para logs; deja dominio visible."""
    s = (addr or "").strip()
    if not s or "@" not in s:
        return s or "?"
    local, _, domain = s.partition("@")
    domain = domain.strip()
    if not domain:
        return "**"
    if len(local) <= 2:
        return f"**@{domain}"
    return f"{local[:2]}***@{domain}"


def _normalize_attachments_for_smtp(
    attachments: Optional[List[AttachmentType]],
) -> List[AttachmentType]:
    """
    Valida y convierte adjuntos a (nombre, bytes). Omite vacios o tipos invalidos.
    Evita enviar multipart/mixed sin partes utiles y mejora compatibilidad con clientes SMTP.
    """
    out: List[AttachmentType] = []
    if not attachments:
        return out
    for idx, item in enumerate(attachments):
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            logger.warning("[SMTP_ENVIO] adjunto #%s ignorado: se esperaba (nombre, bytes)", idx)
            continue
        filename, content = item[0], item[1]
        if filename is None or not str(filename).strip():
            logger.warning("[SMTP_ENVIO] adjunto #%s ignorado: nombre vacio", idx)
            continue
        name = str(filename).strip().replace("\r", "").replace("\n", "")
        if content is None:
            logger.warning("[SMTP_ENVIO] adjunto ignorado contenido None filename=%s", name)
            continue
        if isinstance(content, memoryview):
            raw = content.tobytes()
        elif isinstance(content, bytearray):
            raw = bytes(content)
        elif isinstance(content, bytes):
            raw = content
        else:
            try:
                raw = bytes(content)
            except Exception:
                logger.warning(
                    "[SMTP_ENVIO] adjunto ignorado tipo no binario filename=%s tipo=%s",
                    name,
                    type(content).__name__,
                )
                continue
        if len(raw) == 0:
            logger.warning("[SMTP_ENVIO] adjunto vacio (0 bytes) omitido filename=%s", name)
            continue
        out.append((name, raw))
    return out


# Gmail (552 5.3.4) y muchos SMTP limitan el tamaño total del mensaje (~25 MB con MIME/encoding).
# Umbral conservador en bytes del PDF bruto antes de base64 y cabeceras.
_COBRANZA_RECIBO_SMTP_MAX_BYTES = 18 * 1024 * 1024


def cobros_recibo_attachments_or_oversize_note(
    filename: str,
    pdf_bytes: Optional[bytes],
) -> Tuple[Optional[List[AttachmentType]], str]:
    """
    Devuelve (lista_adjuntos_o_None, sufijo_para_el_cuerpo).

    Si el PDF supera el umbral seguro para SMTP típico, no adjunta y devuelve texto aclaratorio
    para el cuerpo (evita 552 5.3.4 y reduce tiempo bloqueado en envío).
    """
    if not pdf_bytes:
        return None, ""
    raw = bytes(pdf_bytes)
    if len(raw) <= _COBRANZA_RECIBO_SMTP_MAX_BYTES:
        fn = (filename or "recibo.pdf").strip().replace("\r", "").replace("\n", "") or "recibo.pdf"
        return [(fn, raw)], ""
    mb = max(1, int(len(raw) / (1024 * 1024)))
    note = (
        f"\n\n(Nota) El recibo en PDF es demasiado grande para adjuntarlo por este correo (~{mb} MB). "
        "No se adjuntó el archivo para evitar que el servidor lo rechace (límite de tamaño). "
        "Puede solicitar el recibo por WhatsApp o por los canales de atención habituales, indicando su número de referencia.\n"
    )
    logger.info(
        "[SMTP_ENVIO] recibo_pdf omitido por tamano filename=%s bytes=%s umbral=%s",
        filename,
        len(raw),
        _COBRANZA_RECIBO_SMTP_MAX_BYTES,
    )
    return None, note


def cuerpo_parece_html(cuerpo: Optional[str]) -> bool:
    """
    Indica si el cuerpo debe enviarse como text/html (no solo texto plano).
    Lista fija de etiquetas (<p> sin espacio, <ul>, etc.) omitia muchas plantillas reales;
    con adjuntos el cliente mostraba solo la parte text/plain sin el HTML.
    """
    if not cuerpo or "<" not in cuerpo or ">" not in cuerpo:
        return False
    return bool(
        re.search(r"<\s*!?\s*[a-zA-Z]", cuerpo)
        or re.search(r"<\s*/\s*[a-zA-Z]", cuerpo)
    )


def _strip_html_to_plain(html: str, max_len: int = 8000) -> str:
    '''Quita tags y data URLs para usar como parte text/plain cuando el cuerpo es HTML.'''
    if not html or not html.strip():
        return ""
    s = re.sub(r'data:image/[^;]+;base64,[A-Za-z0-9+/=\s]+', '[Imagen]', html, flags=re.DOTALL)
    s = re.sub(r'<!--.*?-->', '', s, flags=re.DOTALL)
    s = re.sub(r'<[^>]+>', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return (s[:max_len] + "...") if len(s) > max_len else (s or "Contenido en HTML. Abra en un cliente compatible.")


def _logo_url_for_email():
    """URL del logo para reemplazar base64 inline en HTML (evita mensaje enorme que Gmail no renderiza)."""
    try:
        from app.core.config import settings
        base = (getattr(settings, "FRONTEND_PUBLIC_URL", None) or "https://rapicredit.onrender.com/pagos").rstrip("/")
    except Exception:
        base = "https://rapicredit.onrender.com/pagos"
    return f"{base}/logos/rapicredit-public.png"


# Longitud mínima de data URL para reemplazar por logo (evita romper iconos SVG pequeños como WhatsApp).
_MIN_BASE64_LENGTH_TO_REPLACE = 300


def _sanitize_html_for_email(html: str, logo_url: str) -> str:
    """
    Asegura que el HTML del correo no esté corrupto al cargarse en el cliente:
    - Reemplaza imágenes inline base64 largas por la URL del logo (evita payload enorme y fallos de render).
    - Sustituye {{LOGO_URL}} / {{logo_url}} por la URL real por si no se reemplazó en plantilla.
    - Corrige typo base64/ -> base64,.
    Soporta src con comillas dobles y simples.
    """
    if not html or not isinstance(html, str):
        return html
    # Corregir typo que rompe data URL
    if "base64/" in html:
        html = html.replace("base64/", "base64,")
    # Reemplazar tokens de logo (plantillas usan LOGO_URL o logo_url)
    html = html.replace("{{LOGO_URL}}", logo_url)
    html = html.replace("{{logo_url}}", logo_url)
    html = html.replace("{{Logo_Url}}", logo_url)
    # Reemplazar src="data:image/..." o src='data:image/...' (solo si es largo = logo/foto, no icono SVG pequeño)
    def replace_data_url(match):
        quote, content = match.group(1), match.group(2)
        if len(content) >= _MIN_BASE64_LENGTH_TO_REPLACE:
            return f'src={quote}{logo_url}{quote}'
        return match.group(0)
    html = re.sub(r'src\s*=\s*(")(data:image/[^"]+)"', replace_data_url, html, flags=re.IGNORECASE)
    html = re.sub(r"src\s*=\s*(')(data:image/[^']+)'", replace_data_url, html, flags=re.IGNORECASE)
    # Si quedo un src con token sin sustituir, forzar URL del logo
    html = re.sub(
        r'src\s*=\s*(["\'])\{\{\s*logo[_-]?url\s*\}\}\1',
        rf'src=\1{logo_url}\1',
        html,
        flags=re.IGNORECASE,
    )
    return html


def preparar_body_html_para_mime(body_html: Optional[str]) -> Optional[str]:
    """
    Misma transformación que ``send_email`` aplica al HTML antes de ``MIMEText``:
    normalización UTF-8 y ``_sanitize_html_for_email`` (logo URL, {{LOGO_URL}}, data URLs largas).

    La vista previa admin del correo Recibos debe usar esto sobre la plantilla en disco para coincidir
    con el cuerpo HTML real del mensaje SMTP.
    """
    if body_html is None:
        return None
    if isinstance(body_html, bytes):
        try:
            body_html = body_html.decode("utf-8")
        except UnicodeDecodeError:
            body_html = body_html.decode("cp1252", errors="replace")
    else:
        try:
            body_html.encode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            body_html = body_html.encode("utf-8", errors="replace").decode("utf-8")
    logo_url = _logo_url_for_email()
    return _sanitize_html_for_email(body_html, logo_url)


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



def _normalize_smtp_exception_text(exc: Exception) -> str:
    """
    smtplib suele exponer SMTPAuthenticationError como (534, b'5.7.9 ...'); str(exc) muestra b'...' crudo.
    Usar smtp_code + smtp_error decodificado para mensajes legibles.
    """
    try:
        import smtplib

        if isinstance(exc, smtplib.SMTPResponseException):
            err = getattr(exc, "smtp_error", b"")
            code = getattr(exc, "smtp_code", None)
            if isinstance(err, (bytes, bytearray)):
                inner = bytes(err).decode("utf-8", errors="replace").replace("\n", " ").strip()
            elif err:
                inner = str(err).strip()
            else:
                inner = ""
            if code is not None and inner:
                return f"{code} {inner}"
            if inner:
                return inner
    except Exception:
        pass
    return str(exc).strip()


def _sanitize_smtp_error(exc: Exception) -> str:
    """Mensaje seguro para el usuario al fallar SMTP (sin contrasenas ni rutas ni repr de bytes)."""
    msg = _normalize_smtp_exception_text(exc)
    if not msg:
        return "Error de conexion SMTP."
    lower = msg.lower()
    if (
        "application-specific password" in lower
        or "invalidsecondfactor" in lower
        or "5.7.9" in lower
        or (
            "534" in msg
            and ("gmail" in lower or "gsmtp" in lower or "application-specific" in lower)
        )
    ):
        return (
            "Gmail rechazo el inicio de sesion: con verificacion en dos pasos activa debe usar una "
            "Contrasena de aplicacion (16 caracteres), no la contrasena habitual. "
            "Google: Cuenta > Seguridad > Contrasenas de aplicaciones. "
            "Workspace: segun politica del admin puede bastar la contrasena normal."
        )
    if "username and password not accepted" in lower or "authentication failed" in lower or "login failed" in lower:
        return "Usuario o contrasena no aceptados. Gmail personal: usa Contrasena de aplicacion. Google Workspace: prueba contrasena normal o App Password segun politica."
    if "connection refused" in lower or "timed out" in lower or "timeout" in lower:
        return "La conexion al servidor SMTP tardo demasiado o fue rechazada. Revisa host, puerto (587 o 465) y red."
    if "ssl" in lower or "certificate" in lower:
        return "Error SSL/TLS. Prueba puerto 587 con TLS o 465 con SSL."
    if "connection unexpectedly closed" in lower or "connection closed" in lower or "serverdisconnected" in lower:
        return "El servidor SMTP cerro la conexion durante el inicio de sesion. En entornos cloud (Render, etc.) suele deberse a restricciones de red o a que Gmail exige Contrasena de aplicacion; revisa puerto (587 o 465) y vuelve a intentar."
    if "daily user sending limit exceeded" in lower or "5.4.5" in msg:
        return "Limite diario de envio de Gmail alcanzado (550 5.4.5). Gmail personal: ~100-500/dia. Espera 24h o usa Google Workspace / otro SMTP para mas envios."
    return msg[:300] if len(msg) <= 300 else msg[:297] + "..."


def _smtp_error_is_transient(exc: BaseException) -> bool:
    """True si conviene reintentar (Gmail cierra sesion tras rafagas / rate limit corto)."""
    raw = str(exc).lower()
    safe = _sanitize_smtp_error(exc).lower() if isinstance(exc, Exception) else raw
    needles = (
        "connection unexpectedly closed",
        "connection closed",
        "serverdisconnected",
        "cerro la conexion",
        "broken pipe",
        "connection reset",
        "timed out",
        "timeout",
        "eof occurred",
        "temporarily unavailable",
        "try again later",
        "421",
        "454",
    )
    blob = raw + " " + safe
    return any(n in blob for n in needles)


def _smtp_deliver(
    *,
    cfg: Dict[str, Any],
    port: int,
    use_tls: bool,
    from_addr: str,
    all_recipients: List[str],
    msg_bytes: bytes,
    smtp_session_metadata: Optional[Dict[str, Any]],
    t0_smtp: float,
) -> dict:
    """Una sesion SMTP: connect + login + sendmail. Devuelve refused dict."""
    if port == 465:
        with smtplib.SMTP_SSL(cfg["smtp_host"], port, timeout=SMTP_TIMEOUT_SECONDS) as server:
            log_phase(
                logger,
                FASE_SMTP_CONEXION,
                True,
                f"SMTP_SSL {cfg['smtp_host']}:{port}",
                duration_ms=(time.time() - t0_smtp) * 1000,
            )
            server.login(cfg["smtp_user"], cfg["smtp_password"])
            if smtp_session_metadata is not None:
                _smtp_capture_socket_metadata(server, smtp_session_metadata)
                smtp_session_metadata["tls"] = True
                smtp_session_metadata["tipo_conexion"] = "SMTP_SSL"
            return server.sendmail(from_addr, all_recipients, msg_bytes) or {}
    with smtplib.SMTP(cfg["smtp_host"], port, timeout=SMTP_TIMEOUT_SECONDS) as server:
        if use_tls:
            server.starttls()
        log_phase(
            logger,
            FASE_SMTP_CONEXION,
            True,
            f"SMTP {cfg['smtp_host']}:{port} TLS={use_tls}",
            duration_ms=(time.time() - t0_smtp) * 1000,
        )
        server.login(cfg["smtp_user"], cfg["smtp_password"])
        if smtp_session_metadata is not None:
            _smtp_capture_socket_metadata(server, smtp_session_metadata)
            smtp_session_metadata["tls"] = bool(use_tls)
            smtp_session_metadata["tipo_conexion"] = "SMTP_STARTTLS" if use_tls else "SMTP"
        return server.sendmail(from_addr, all_recipients, msg_bytes) or {}


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
    t0_imap = time.time()
    try:
        import imaplib
        log_phase(logger, FASE_IMAP_CONEXION, True, f"conectando {imap_host}:{imap_port} SSL={imap_use_ssl}")
        if imap_use_ssl:
            server = imaplib.IMAP4_SSL(imap_host, imap_port, timeout=IMAP_TIMEOUT_SECONDS)
        else:
            server = imaplib.IMAP4(imap_host, imap_port, timeout=IMAP_TIMEOUT_SECONDS)
            server.starttls()
        log_phase(logger, FASE_IMAP_LOGIN, True, f"LOGIN para {imap_user}")

        server.login(imap_user, imap_password)

        _, mailboxes = server.list()
        log_phase(logger, FASE_IMAP_LIST, True, f"{len(mailboxes) if mailboxes else 0} carpetas", duration_ms=(time.time() - t0_imap) * 1000)
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
        
        log_phase(logger, FASE_IMAP_COMPLETA, True, f"{len(folder_list)} carpetas", duration_ms=(time.time() - t0_imap) * 1000)
        return True, None, folder_list

    except Exception as e:
        log_phase(logger, FASE_IMAP_COMPLETA, False, str(e))
        logger.exception("Error probando IMAP %s:%s para usuario %s", imap_host, imap_port, imap_user)
        error_msg = _sanitize_imap_error(e)
        return False, error_msg, None


def test_smtp_connection(cfg: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Prueba login SMTP (connect + auth) sin enviar correo.
    cfg: smtp_host, smtp_port, smtp_user, smtp_password, smtp_use_tls.
    """
    host = (cfg.get("smtp_host") or "").strip()
    user = (cfg.get("smtp_user") or "").strip()
    pwd = (cfg.get("smtp_password") or "").strip()
    if not host:
        return False, "Falta servidor SMTP."
    if not user:
        return False, "Falta usuario SMTP."
    if not pwd or pwd == "***":
        return False, "Falta contrasena SMTP (use contrasena de aplicacion en Gmail)."
    try:
        port = int(cfg.get("smtp_port") or 587)
    except (TypeError, ValueError):
        port = 587
    use_tls = str(cfg.get("smtp_use_tls", "true")).lower() in ("true", "1", "yes")
    t0 = time.time()
    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=SMTP_TIMEOUT_SECONDS) as server:
                server.login(user, pwd)
        else:
            with smtplib.SMTP(host, port, timeout=SMTP_TIMEOUT_SECONDS) as server:
                if use_tls:
                    server.starttls()
                server.login(user, pwd)
        log_phase(
            logger,
            FASE_SMTP_CONEXION,
            True,
            f"test SMTP OK {host}:{port} user={user}",
            duration_ms=(time.time() - t0) * 1000,
        )
        return True, None
    except Exception as e:
        log_phase(logger, FASE_SMTP_CONEXION, False, str(e))
        return False, _sanitize_smtp_error(e)


def _message_id_domain(from_header: str, smtp_host: str) -> str:
    if from_header and "@" in from_header:
        dom = from_header.split("@")[-1].strip().rstrip(">").strip()
        if dom:
            return dom
    h = (smtp_host or "localhost").split(":")[0].strip()
    return h or "localhost"


def _smtp_capture_socket_metadata(server: Any, target: Dict[str, Any]) -> None:
    sock = getattr(server, "sock", None)
    if sock is None:
        return
    try:
        peer = sock.getpeername()
        target["ip_servidor_smtp_conectado"] = peer[0]
        target["puerto_servidor_smtp_conectado"] = peer[1]
    except OSError:
        pass
    try:
        loc = sock.getsockname()
        target["ip_socket_local_proceso"] = loc[0]
        target["puerto_socket_local"] = loc[1]
    except OSError:
        pass



def _enviar_copia_cco_desde_cuenta_cobros(
    *,
    to_email: str,
    subject: str,
    body_text: str,
    body_html: Optional[str],
    attachments: Optional[List[Tuple[str, bytes]]],
) -> Tuple[bool, Optional[str]]:
    """Copia de auditoria a notificaciones@: To real via SMTP cuenta cobros (pagos@)."""
    dest = (to_email or "").strip()
    if not dest or "@" not in dest:
        return False, "destino invalido"
    if dest.lower() == "itmaster@rapicreditca.com":
        return False, "itmaster no es destino de copia CCO"
    cfg = get_smtp_config(servicio="cobros")
    if not cfg.get("smtp_host") or not (cfg.get("smtp_user") or "").strip():
        return False, "sin SMTP cobros"
    if not (cfg.get("smtp_password") or "").strip() or (cfg.get("smtp_password") or "").strip() == "***":
        return False, "sin password SMTP cobros"
    from_addr = (cfg.get("from_email") or cfg.get("smtp_user") or "").strip()
    if from_addr.lower() == dest.lower() or (cfg.get("smtp_user") or "").strip().lower() == dest.lower():
        cfg = get_smtp_config(servicio="estado_cuenta")
        from_addr = (cfg.get("from_email") or cfg.get("smtp_user") or "").strip()
        if from_addr.lower() == dest.lower():
            return False, "no hay cuenta SMTP distinta de notificaciones@ para la copia"
    try:
        from email import encoders
        from email.mime.application import MIMEApplication
        from email.mime.base import MIMEBase
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        plain = body_text or ""
        html = body_html
        if html is not None:
            html = preparar_body_html_para_mime(html)
        atts = list(attachments or [])
        if atts:
            msg = MIMEMultipart("mixed")
            alt = MIMEMultipart("alternative")
            alt.attach(MIMEText(plain, "plain", "utf-8"))
            if html:
                alt.attach(MIMEText(html, "html", "utf-8"))
            msg.attach(alt)
            for filename, content in atts:
                if (filename or "").lower().endswith(".pdf"):
                    part = MIMEApplication(content, _subtype="pdf")
                else:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(content)
                    encoders.encode_base64(part)
                part.add_header("Content-Disposition", "attachment", filename=filename)
                msg.attach(part)
        else:
            msg = MIMEMultipart("alternative")
            msg.attach(MIMEText(plain, "plain", "utf-8"))
            if html:
                msg.attach(MIMEText(html, "html", "utf-8"))
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = dest
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = f"<{uuid.uuid4().hex}@{_message_id_domain(from_addr, str(cfg.get('smtp_host') or ''))}>"
        port = int(cfg.get("smtp_port") or 587)
        use_tls = (cfg.get("smtp_use_tls") or "true").lower() == "true"
        msg_str = msg.as_string(policy=__import__("email").policy.SMTP)
        msg_bytes = msg_str.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8")
        t0 = time.time()
        refused = _smtp_deliver(
            cfg=cfg,
            port=port,
            use_tls=use_tls,
            from_addr=from_addr,
            all_recipients=[dest],
            msg_bytes=msg_bytes,
            smtp_session_metadata=None,
            t0_smtp=t0,
        )
        if refused:
            return False, f"smtp refused: {refused}"
        return True, None
    except Exception as e:
        return False, _sanitize_smtp_error(e)


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
    servicio: Optional[str] = None,
    tipo_tab: Optional[str] = None,
    smtp_session_metadata: Optional[Dict[str, Any]] = None,
    aplicar_cco_automatica: bool = True,
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
        logger.info("[SMTP_ENVIO] estado=abortado razon=sin_destinatarios servicio=%s tipo_tab=%s", servicio or "", tipo_tab or "")
        if smtp_session_metadata is not None:
            smtp_session_metadata.clear()
            smtp_session_metadata.update({"resultado": "no_intentado", "motivo": "sin_destinatarios"})
        return False, "No hay destinatarios."
    sync_from_db()
    dest_solicitados_originales = [str(e).strip() for e in to_emails if e is not None and str(e).strip()]
    # Modo Pruebas: redirigir todos los env�os al correo(s) de pruebas (desde notificaciones_envios o email_config)
    # EXCEPCI�N: si respetar_destinos_manuales=True (ej. usuario hizo clic en "Enviar Email de Prueba"), se env�an a los correos indicados en la interfaz.
    modo_pruebas, emails_pruebas_list = get_modo_pruebas_email(servicio=servicio)
    log_phase(logger, FASE_MODO_PRUEBAS, True, "modo_pruebas=%s servicio=%s" % (modo_pruebas, servicio or "global"))
    redirigido_modo_pruebas = bool(modo_pruebas and emails_pruebas_list and not respetar_destinos_manuales)
    if redirigido_modo_pruebas:
        _svc_pre = (servicio or "").strip().lower()
        _pruebas_ok = [
            e for e in emails_pruebas_list
            if e and str(e).strip().lower() != "itmaster@rapicreditca.com"
        ]
        # Notificaciones/Recibos: NUNCA redirigir a itmaster@ (mantener To original del cliente).
        if _svc_pre in ("notificaciones", "recibos") and not _pruebas_ok:
            redirigido_modo_pruebas = False
            cc_list = [e.strip() for e in (cc_emails or []) if e and isinstance(e, str) and "@" in e.strip()]
            bcc_list = [e.strip() for e in (bcc_emails or []) if e and isinstance(e, str) and "@" in e.strip()]
            logger.warning(
                "[SMTP_ENVIO] modo_pruebas IGNORADO servicio=%s: email_pruebas solo itmaster@; "
                "se mantiene To original=%s",
                _svc_pre,
                [mask_email_for_log(x) for x in dest_solicitados_originales],
            )
        else:
            to_emails = _pruebas_ok if (_svc_pre in ("notificaciones", "recibos") and _pruebas_ok) else emails_pruebas_list
            to_emails = [e for e in to_emails if str(e).strip().lower() != "itmaster@rapicreditca.com"]
            if not to_emails:
                # NUNCA restaurar itmaster; usar originales sin itmaster o notificaciones@.
                to_emails = [
                    e for e in dest_solicitados_originales
                    if e and str(e).strip().lower() != "itmaster@rapicreditca.com"
                ]
                if not to_emails and _svc_pre in ("notificaciones", "recibos"):
                    to_emails = ["notificaciones@rapicreditca.com"]
            cc_list = []
            bcc_list = [
                e.strip()
                for e in (bcc_emails or [])
                if e and isinstance(e, str) and "@" in e.strip()
            ]
            to_low = {str(x).strip().lower() for x in to_emails if x}
            bcc_list = [b for b in bcc_list if b.lower() not in to_low]
            logger.info(
                "[SMTP_ENVIO] modo_pruebas=1 redirigido=1 servicio=%s tipo_tab=%s solicitados_MASK=%s efectivos=%s bcc=%s",
                servicio or "",
                tipo_tab or "",
                [mask_email_for_log(x) for x in dest_solicitados_originales],
                list(to_emails),
                [mask_email_for_log(x) for x in bcc_list],
            )
            logger.info("Modo Pruebas: envio redirigido a %s (CCO conservado: %s)", to_emails, bcc_list)
    else:
        # Destino explícito (p. ej. «Enviar prueba» con To manual): no exigir lista de pruebas aunque el servicio esté en modo pruebas.
        if modo_pruebas and not emails_pruebas_list and not respetar_destinos_manuales:
            log_phase(logger, FASE_SMTP_CONFIG, False, "modo pruebas sin email de pruebas configurado")
            logger.warning(
                "[SMTP_ENVIO] estado=abortado razon=modo_pruebas_sin_correo servicio=%s tipo_tab=%s solicitados_MASK=%s",
                servicio or "",
                tipo_tab or "",
                [mask_email_for_log(x) for x in dest_solicitados_originales],
            )
            logger.warning(
                "Modo Pruebas activo pero no hay correo de pruebas configurado. "
                + (
                    "Configure correo(s) en Configuracion > Email (servicio recibos no usa notificaciones_envios)."
                    if (servicio or "").strip().lower() == "recibos"
                    else "Configure en Notificaciones > Configuracion (envios) o en Configuracion > Email."
                )
            )
            if smtp_session_metadata is not None:
                smtp_session_metadata.clear()
                smtp_session_metadata.update(
                    {"resultado": "no_intentado", "motivo": "modo_pruebas_sin_correo_pruebas"}
                )
            if (servicio or "").strip().lower() == "recibos":
                return False, (
                    "En modo Pruebas (Recibos) debe configurar al menos un correo de prueba en Configuracion > Email."
                )
            return False, (
                "En modo Pruebas debe configurar el correo de pruebas en Notificaciones > Configuracion (envios) "
                "o en Configuracion > Email."
            )
        cc_list = [e.strip() for e in (cc_emails or []) if e and isinstance(e, str) and "@" in e.strip()]
        bcc_list = [e.strip() for e in (bcc_emails or []) if e and isinstance(e, str) and "@" in e.strip()]

    svc_low = (servicio or "").strip().lower()
    # Direcciones que Workspace/Gmail a menudo no entregan si van solo en BCC
    # (grupo, misma cuenta SMTP, alias). Se reenvian luego como To aparte.
    force_to_cco: List[str] = []

    if aplicar_cco_automatica and svc_low == "recibos":
        extra_bcc = get_recibos_bcc_emails()
        if extra_bcc:
            seen_b = {x.lower() for x in bcc_list}
            for addr in extra_bcc:
                a = (addr or "").strip()
                if not a or "@" not in a:
                    continue
                low = a.lower()
                if low in seen_b:
                    continue
                seen_b.add(low)
                bcc_list.append(a)

    # CCO global obligatoria para notificaciones y recibos (NOTIFICACIONES_BCC_GLOBAL).
    if aplicar_cco_automatica and svc_low in ("notificaciones", "recibos"):
        _raw_global = getattr(settings, "NOTIFICACIONES_BCC_GLOBAL", "") or ""
        if not str(_raw_global).strip():
            _raw_global = "notificaciones@rapicreditca.com,cobranza@rapicreditca.com"
        _seen_bcc = {x.lower() for x in bcc_list}
        for _chunk in str(_raw_global).replace(";", ",").split(","):
            _addr = _chunk.strip()
            if not _addr or "@" not in _addr:
                continue
            _low = _addr.lower()
            if _low in _seen_bcc:
                continue
            _seen_bcc.add(_low)
            bcc_list.append(_addr)
        to_low_final = {str(x).strip().lower() for x in to_emails if x}
        bcc_list = [b for b in bcc_list if b.lower() not in to_low_final]
        logger.info(
            "[SMTP_ENVIO] cco_efectivo servicio=%s to=%s bcc=%s (recibos_bcc_ui+global)",
            svc_low,
            list(to_emails),
            bcc_list,
        )

    # Saneo final: descartar destinatarios que smtplib no podra encodear a ASCII para
    # el RCPT TO (p. ej. emails corrompidos con U+FFFD por mojibake en la BD).
    # Sin esto, sendmail() revienta con UnicodeEncodeError y el correo queda como
    # "ok_email_fail" sin razon visible en la UI.
    def _es_destino_smtp_valido(direccion: str) -> bool:
        s = (direccion or "").strip()
        if not s or "@" not in s:
            return False
        if "\ufffd" in s:
            return False
        try:
            s.encode("ascii")
        except UnicodeEncodeError:
            return False
        for ch in s:
            if ord(ch) < 0x20 or ord(ch) == 0x7F or ch == " ":
                return False
        return True

    def _filtrar_smtp(lista: List[str], etiqueta: str) -> List[str]:
        validos: List[str] = []
        descartados: List[str] = []
        for direccion in lista:
            if _es_destino_smtp_valido(direccion):
                validos.append(direccion.strip())
            else:
                descartados.append(direccion)
        if descartados:
            logger.warning(
                "[SMTP_ENVIO] destinatarios %s descartados por caracteres invalidos (no-ASCII/U+FFFD): %s",
                etiqueta,
                [mask_email_for_log(d) for d in descartados],
            )
        return validos

    to_emails_filtrados = _filtrar_smtp(list(to_emails), "TO")
    cc_list = _filtrar_smtp(cc_list, "CC")
    bcc_list = _filtrar_smtp(bcc_list, "BCC")

    if not to_emails_filtrados:
        log_phase(logger, FASE_SMTP_CONFIG, False, "destinatarios invalidos (no-ASCII/U+FFFD)")
        logger.warning(
            "[SMTP_ENVIO] estado=abortado razon=destinatarios_invalidos servicio=%s tipo_tab=%s solicitados_MASK=%s",
            servicio or "",
            tipo_tab or "",
            [mask_email_for_log(x) for x in dest_solicitados_originales],
        )
        if smtp_session_metadata is not None:
            smtp_session_metadata.clear()
            smtp_session_metadata.update(
                {"resultado": "no_intentado", "motivo": "destinatarios_invalidos"}
            )
        return False, (
            "Los destinatarios contienen caracteres invalidos (mojibake/no-ASCII). "
            "Revise el email registrado del cliente y corrijalo antes de reintentar."
        )

    to_emails = to_emails_filtrados

    # Bloqueo final: notificaciones/recibos NUNCA envian To a itmaster@.
    if (servicio or "").strip().lower() in ("notificaciones", "recibos"):
        _before = list(to_emails)
        to_emails = [e for e in to_emails if (e or "").strip().lower() != "itmaster@rapicreditca.com"]
        if _before and not to_emails:
            to_emails = [
                e for e in dest_solicitados_originales
                if e and e.lower() != "itmaster@rapicreditca.com" and _es_destino_smtp_valido(e)
            ]
        if not to_emails:
            to_emails = ["notificaciones@rapicreditca.com"]
            logger.warning(
                "[SMTP_ENVIO] To itmaster@ bloqueado servicio=%s; To sustituido por notificaciones@",
                (servicio or "").strip().lower(),
            )
        else:
            logger.info(
                "[SMTP_ENVIO] To sin itmaster servicio=%s to=%s (antes=%s)",
                (servicio or "").strip().lower(),
                to_emails,
                _before,
            )

    attachments_norm = _normalize_attachments_for_smtp(attachments)
    has_attachments = len(attachments_norm) > 0
    if attachments and not attachments_norm:
        logger.warning(
            "[SMTP_ENVIO] se recibieron %s adjuntos pero ninguno es valido (nombre/contenido)",
            len(attachments),
        )
    cfg = get_smtp_config(servicio=servicio, tipo_tab=tipo_tab)
    if not cfg.get("smtp_host") or not cfg.get("smtp_user"):
        log_phase(logger, FASE_SMTP_CONFIG, False, "falta smtp_host o smtp_user")
        logger.warning(
            "[SMTP_ENVIO] estado=abortado razon=sin_smtp_config servicio=%s tipo_tab=%s modo_pruebas=%s redirigido=%s",
            servicio or "",
            tipo_tab or "",
            modo_pruebas,
            redirigido_modo_pruebas,
        )
        if smtp_session_metadata is not None:
            smtp_session_metadata.clear()
            smtp_session_metadata.update({"resultado": "no_intentado", "motivo": "sin_smtp_config"})
        return False, "No hay servidor SMTP configurado. Configura en Configuracion > Email."
    if not (cfg.get("smtp_password") or "").strip() or (cfg.get("smtp_password") or "").strip() == "***":
        log_phase(logger, FASE_SMTP_CONFIG, False, "falta contrasena SMTP")
        logger.warning(
            "[SMTP_ENVIO] estado=abortado razon=sin_smtp_password servicio=%s tipo_tab=%s modo_pruebas=%s redirigido=%s",
            servicio or "",
            tipo_tab or "",
            modo_pruebas,
            redirigido_modo_pruebas,
        )
        if smtp_session_metadata is not None:
            smtp_session_metadata.clear()
            smtp_session_metadata.update({"resultado": "no_intentado", "motivo": "sin_smtp_password"})
        return False, "Falta contrasena SMTP. Configura en Configuracion > Email."
    log_phase(logger, FASE_SMTP_CONFIG, True, "host=%s port=%s" % (cfg.get("smtp_host"), cfg.get("smtp_port")))

    # notificaciones@: Gmail/Workspace suele ignorar CCO-only. Se deja en BCC (por si llega)
    # Y ademas se fuerza copia To desde cuenta cobros/pagos@.
    if aplicar_cco_automatica and svc_low in ("notificaciones", "recibos"):
        _sender_ids = {
            (cfg.get("smtp_user") or "").strip().lower(),
            (cfg.get("from_email") or "").strip().lower(),
        }
        _to_low = {str(x).strip().lower() for x in to_emails if x}
        _kept: List[str] = []
        _seen_force: set[str] = {x.lower() for x in force_to_cco}
        for _b in bcc_list:
            _bl = (_b or "").lower()
            if not _bl:
                continue
            # Autoenvio (mismo From/smtp): no sirve en BCC; solo copia To aparte.
            if _bl in _sender_ids and _bl not in _to_low:
                if _bl not in _seen_force:
                    force_to_cco.append(_b)
                    _seen_force.add(_bl)
                continue
            _kept.append(_b)
            if _bl == "notificaciones@rapicreditca.com" and _bl not in _to_low and _bl not in _seen_force:
                force_to_cco.append(_b)
                _seen_force.add(_bl)
        # Garantizar copia a notificaciones@ aunque no estuviera en BCC.
        if "notificaciones@rapicreditca.com" not in _to_low and "notificaciones@rapicreditca.com" not in _seen_force:
            force_to_cco.append("notificaciones@rapicreditca.com")
            _seen_force.add("notificaciones@rapicreditca.com")
        if "cobranza@rapicreditca.com" not in {x.lower() for x in _kept} and "cobranza@rapicreditca.com" not in _to_low:
            _kept.append("cobranza@rapicreditca.com")
        bcc_list = _kept
        logger.info(
            "[SMTP_ENVIO] cco_final servicio=%s to=%s bcc=%s force_to=%s",
            svc_low,
            list(to_emails),
            bcc_list,
            force_to_cco,
        )

    solicitados_mask = [mask_email_for_log(x) for x in dest_solicitados_originales]
    efectivos_para_smtp = list(to_emails) + cc_list + bcc_list
    adjuntos_log = [(n, len(b)) for n, b in attachments_norm]
    logger.debug(
        "[SMTP_ENVIO] intento modo_pruebas=%s redirigido_modo_pruebas=%s servicio=%s tipo_tab=%s "
        "respetar_destinos_manuales=%s solicitados_MASK=%s efectivos_smtp=%s asunto=%s adjuntos_n=%s adjuntos_bytes=%s smtp_host=%s",
        modo_pruebas,
        redirigido_modo_pruebas,
        servicio or "",
        tipo_tab or "",
        respetar_destinos_manuales,
        solicitados_mask,
        efectivos_para_smtp,
        (subject or "")[:200],
        len(attachments_norm),
        adjuntos_log,
        cfg.get("smtp_host") or "",
    )

    try:
        import smtplib
        from email import encoders
        from email.mime.application import MIMEApplication
        from email.mime.base import MIMEBase
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        if smtp_session_metadata is not None:
            smtp_session_metadata.clear()
            smtp_session_metadata.update(
                {
                    "fecha_registro_utc": datetime.now(timezone.utc).isoformat(),
                    "servidor_smtp_host": cfg.get("smtp_host"),
                    "servidor_smtp_puerto": int(cfg.get("smtp_port") or 587),
                    "modo_pruebas_redirigido": redirigido_modo_pruebas,
                    "destinatarios_sesion_smtp": list(efectivos_para_smtp),
                }
            )

        # Asegurar body_text y body_html son str y UTF-8 validos
        if body_text is None:
            body_text = ""
        if isinstance(body_text, bytes):
            try:
                body_text = body_text.decode("utf-8")
            except UnicodeDecodeError:
                body_text = body_text.decode("cp1252", errors="replace")
        else:
            try:
                body_text.encode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                body_text = body_text.encode("utf-8", errors="replace").decode("utf-8")
        # Si el caller envió HTML solo en body_text (sin body_html), detectar y enviar como HTML
        if body_html is None and body_text and cuerpo_parece_html(body_text):
            body_html = body_text
        # Asegurar body_html es str UTF-8 válido + mismo saneado que la vista previa admin (logo URL, etc.)
        if body_html is not None:
            body_html = preparar_body_html_para_mime(body_html)

        # Gmail: si body_text es HTML, usar version solo texto para text/plain (evita ver codigo+base64)
        if body_html and body_text and ("<" in body_text and ">" in body_text):
            body_text = _strip_html_to_plain(body_text)
        if body_html and (not body_text or not body_text.strip()):
            body_text = "Contenido en HTML. Si no ve el formato correcto, abra el correo en Gmail o otro cliente compatible."

        if has_attachments:
            msg = MIMEMultipart("mixed")
            alt = MIMEMultipart("alternative")
            alt.attach(MIMEText(body_text, "plain", "utf-8"))
            if body_html:
                alt.attach(MIMEText(body_html, "html", "utf-8"))
            msg.attach(alt)
        else:
            msg = MIMEMultipart("alternative")
            msg.attach(MIMEText(body_text, "plain", "utf-8"))
            if body_html:
                msg.attach(MIMEText(body_html, "html", "utf-8"))

        msg["Subject"] = subject
        msg["From"] = cfg.get("from_email") or cfg.get("smtp_user")
        _from_hdr = str(msg["From"] or "")
        _mid_domain = _message_id_domain(_from_hdr, str(cfg.get("smtp_host") or ""))
        _message_id = f"<{uuid.uuid4().hex}@{_mid_domain}>"
        msg["Message-ID"] = _message_id
        if smtp_session_metadata is not None:
            smtp_session_metadata["message_id_rfc5322"] = _message_id
        msg["Date"] = formatdate(localtime=True)

        # === GATE ABSOLUTO notificaciones/recibos (ANTES de escribir To/Cc; no duplicar cabeceras) ===
        if svc_low in ("notificaciones", "recibos"):
            _itm = "itmaster@rapicreditca.com"
            _not = "notificaciones@rapicreditca.com"
            _cob = "cobranza@rapicreditca.com"
            to_emails = [e for e in to_emails if (e or "").strip().lower() != _itm]
            cc_list = [e for e in cc_list if (e or "").strip().lower() != _itm]
            bcc_list = [e for e in bcc_list if (e or "").strip().lower() != _itm]
            if not to_emails:
                to_emails = [_not]
            _bcc_low = {x.lower() for x in bcc_list}
            _to_low = {x.lower() for x in to_emails}
            if _cob not in _bcc_low and _cob not in _to_low:
                bcc_list.append(_cob)
            if _not not in _to_low:
                if _not not in {x.lower() for x in force_to_cco}:
                    force_to_cco.append(_not)
            logger.info(
                "[SMTP_ENVIO] GATE_ABSOLUTO v3-single-to servicio=%s to=%s bcc=%s force_to=%s from=%s",
                svc_low,
                to_emails,
                bcc_list,
                force_to_cco,
                cfg.get("from_email") or cfg.get("smtp_user"),
            )

        # Una sola cabecera To (Gmail 550 si hay To duplicado).
        msg["To"] = ", ".join(to_emails)
        if cc_list:
            msg["Cc"] = ", ".join(cc_list)
        # CCO/BCC: no escribir cabecera "Bcc" en el RFC822. Va solo en el sobre SMTP (sendmail RCPT TO).

        if has_attachments:
            for filename, content in attachments_norm:
                fn_lower = filename.lower()
                if fn_lower.endswith(".pdf"):
                    part = MIMEApplication(content, _subtype="pdf")
                else:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(content)
                    encoders.encode_base64(part)
                part.add_header("Content-Disposition", "attachment", filename=filename)
                msg.attach(part)

        port = int(cfg.get("smtp_port") or 587)
        all_recipients = to_emails + cc_list + bcc_list
        use_tls = (cfg.get("smtp_use_tls") or "true").lower() == "true"
        msg_str = msg.as_string(policy=__import__("email").policy.SMTP)
        msg_bytes = msg_str.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8")
        t0_smtp = time.time()
        refused: dict = {}
        last_exc: Optional[BaseException] = None
        for attempt in range(1, SMTP_SEND_MAX_ATTEMPTS + 1):
            try:
                refused = _smtp_deliver(
                    cfg=cfg,
                    port=port,
                    use_tls=use_tls,
                    from_addr=msg["From"],
                    all_recipients=all_recipients,
                    msg_bytes=msg_bytes,
                    smtp_session_metadata=smtp_session_metadata,
                    t0_smtp=t0_smtp,
                )
                last_exc = None
                break
            except Exception as e:
                last_exc = e
                if attempt >= SMTP_SEND_MAX_ATTEMPTS or not _smtp_error_is_transient(e):
                    raise
                wait_s = SMTP_RETRY_BASE_SECONDS * attempt
                logger.warning(
                    "[SMTP_ENVIO] reintento %s/%s en %.1fs tras error transitorio: %s",
                    attempt,
                    SMTP_SEND_MAX_ATTEMPTS,
                    wait_s,
                    _sanitize_smtp_error(e)[:200],
                )
                time.sleep(wait_s)
        if last_exc is not None:
            raise last_exc
        if refused:
            log_phase(logger, FASE_SMTP_ENVIO, False, f"smtp_rechazo_destinatarios={refused}", duration_ms=(time.time() - t0_smtp) * 1000)
            logger.warning(
                "[SMTP_ENVIO] estado=rechazo_destinatarios modo_pruebas=%s redirigido_modo_pruebas=%s refused=%s efectivos=%s asunto=%s",
                modo_pruebas,
                redirigido_modo_pruebas,
                refused,
                all_recipients,
                (subject or "")[:200],
            )
            logger.warning(
                "SMTP acepto sesion pero rechazo destinatarios refused=%s from=%s subject=%s",
                refused,
                msg.get("From"),
                subject,
            )
            if smtp_session_metadata is not None:
                smtp_session_metadata["resultado"] = "rechazo_smtp_por_destinatario"
                smtp_session_metadata["smtp_refused"] = str(refused)[:2000]
            return False, "El servidor SMTP rechazo uno o mas destinatarios: %s" % (refused,)
        log_phase(
            logger,
            FASE_SMTP_ENVIO,
            True,
            f"destinos={len(all_recipients)} smtp_acepto_envio=si",
            duration_ms=(time.time() - t0_smtp) * 1000,
        )
        dur_ms = (time.time() - t0_smtp) * 1000
        logger.info(
            "[SMTP_ENVIO] estado=aceptado modo_pruebas=%s redirigido_modo_pruebas=%s servicio=%s tipo_tab=%s "
            "destinatarios=%s duracion_ms=%.0f asunto=%s from=%s",
            modo_pruebas,
            redirigido_modo_pruebas,
            servicio or "",
            tipo_tab or "",
            all_recipients,
            dur_ms,
            (subject or "")[:200],
            msg.get("From"),
        )
        logger.debug(
            "Correo aceptado por SMTP (sendmail OK, sin rechazos): to=%s subject=%s from=%s",
            all_recipients,
            subject,
            msg.get("From"),
        )
        if smtp_session_metadata is not None:
            smtp_session_metadata["resultado"] = "aceptado_por_servidor_smtp"

        # Copia aparte (To) para buzones que no reciben CCO-only (p. ej. notificaciones@).
        # Se envia desde cuenta cobros/pagos@ (no desde notificaciones@) para que Gmail
        # lo entregue en bandeja de entrada y no lo trague como autoenvio/CCO de grupo.
        if force_to_cco and aplicar_cco_automatica:
            subj_cco = subject or ""
            if not subj_cco.lower().startswith("[copia cco]"):
                subj_cco = "[Copia CCO] " + subj_cco
            for _addr_cco in force_to_cco:
                try:
                    ok_cco, err_cco = _enviar_copia_cco_desde_cuenta_cobros(
                        to_email=_addr_cco,
                        subject=subj_cco,
                        body_text=body_text,
                        body_html=body_html,
                        attachments=attachments_norm if has_attachments else None,
                    )
                    logger.info(
                        "[SMTP_ENVIO] copia_cco_forzada to=%s ok=%s err=%s via=cobros",
                        _addr_cco,
                        ok_cco,
                        (err_cco or "")[:200],
                    )
                except Exception as _e_cco:
                    logger.warning(
                        "[SMTP_ENVIO] copia_cco_forzada fallo to=%s err=%s",
                        _addr_cco,
                        _e_cco,
                    )

        return True, None
    except Exception as e:
        err_msg = _sanitize_smtp_error(e)
        log_phase(logger, FASE_SMTP_ENVIO, False, err_msg[:500])
        logger.warning(
            "[SMTP_ENVIO] estado=error_excepcion modo_pruebas=%s redirigido_modo_pruebas=%s servicio=%s tipo_tab=%s err=%s",
            modo_pruebas,
            redirigido_modo_pruebas,
            servicio or "",
            tipo_tab or "",
            err_msg[:400],
        )
        if "límite diario" in err_msg.lower() or (
            "daily" in str(e).lower() and "sending limit" in str(e).lower()
        ):
            logger.warning(
                "LIMITE DIARIO GMAIL ALCANZADO: Gmail rechaza mas envios hasta mañana. "
                "Opciones: 1) Esperar 24h 2) Usar SMTP de proveedor transaccional (SendGrid, Mailgun, SES, Resend) en Configuracion > Email. "
                "Ver docs/LIMITE_EMAIL_GMAIL.md"
            )
        if isinstance(e, smtplib.SMTPException):
            logger.error("Error enviando correo (SMTP): %s", err_msg)
        else:
            logger.exception("Error enviando correo: %s", e)
        if smtp_session_metadata is not None:
            smtp_session_metadata["resultado"] = "error_excepcion"
            smtp_session_metadata["error_resumen"] = err_msg[:2000]
        return False, err_msg


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

    ok, _ = send_email(to_list, subject, body, attachments=attachments if attachments else None, servicio="tickets")
    return ok


def notify_ticket_updated(ticket_id: int, titulo: str, estado: str, prioridad: str) -> bool:
    """Notifica por correo que se actualiz� un ticket. Destino: contactos prestablecidos."""
    to_list = get_tickets_notify_emails()
    if not to_list:
        return False
    subject = f"[CRM] Ticket #{ticket_id} actualizado: {estado}"
    body = f"Ticket #{ticket_id}: {titulo}\nEstado: {estado}\nPrioridad: {prioridad}\n"
    ok, _ = send_email(to_list, subject, body, servicio="tickets")
    return ok
