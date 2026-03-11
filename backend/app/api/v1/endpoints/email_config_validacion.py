"""
Validación y legitimación de la configuración de email antes de guardar o probar.

- Formato de direcciones de correo (smtp_user, from_email, email_pruebas, tickets_notify_emails).
- Puertos permitidos: SMTP 587 (TLS), 465 (SSL); IMAP 993 (SSL), 143 (STARTTLS).
- Campos obligatorios según modo (modo_pruebas requiere email_pruebas).
- Una sola fuente de verdad: la BD; las operaciones de lectura cargan desde BD;
  el guardado valida → fusiona → persiste → actualiza holder.
"""
import re
from typing import Any, List, Optional, Tuple

# Puertos estándar Gmail/Google (Ref: https://support.google.com/mail/answer/7126229)
SMTP_PUERTOS_PERMITIDOS = (587, 465)
IMAP_PUERTOS_PERMITIDOS = (993, 143)

# Regex simple para email (evitar inyección y formatos inválidos)
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)


def _validar_formato_email(email: str) -> bool:
    """True si la cadena tiene formato de email válido (usuario@dominio.tld)."""
    if not email or not isinstance(email, str):
        return False
    s = email.strip()
    if len(s) > 254 or not s:
        return False
    return bool(EMAIL_REGEX.match(s))


def validar_emails_lista(valor: Optional[str]) -> Tuple[bool, List[str]]:
    """
    Valida una lista de emails separados por coma (ej. tickets_notify_emails).
    Devuelve (True, [emails válidos]) o (False, [mensajes de error]).
    """
    if not valor or not isinstance(valor, str):
        return True, []
    errores: List[str] = []
    validos: List[str] = []
    for part in valor.split(","):
        s = part.strip()
        if not s:
            continue
        if not _validar_formato_email(s):
            errores.append(f"Email inválido: '{s[:50]}'")
        else:
            validos.append(s)
    return (len(errores) == 0, validos if not errores else errores)


def validar_config_email_para_guardar(data: dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Valida la configuración de email antes de persistir.
    Devuelve (True, []) si todo es válido; (False, [errores]) en caso contrario.
    """
    errores: List[str] = []

    # Campos obligatorios SMTP
    smtp_host = (data.get("smtp_host") or "").strip()
    smtp_port_raw = data.get("smtp_port")
    smtp_user = (data.get("smtp_user") or "").strip()
    from_email = (data.get("from_email") or "").strip()

    if not smtp_host:
        errores.append("Falta servidor SMTP.")
    if not smtp_user:
        errores.append("Falta email de usuario SMTP.")
    else:
        if not _validar_formato_email(smtp_user):
            errores.append("El email de usuario SMTP no tiene formato válido.")
    if not from_email:
        errores.append("Falta email del remitente.")
    else:
        if not _validar_formato_email(from_email):
            errores.append("El email del remitente no tiene formato válido.")

    # Puerto SMTP numérico y permitido
    try:
        smtp_port = int(smtp_port_raw) if smtp_port_raw is not None else 587
    except (TypeError, ValueError):
        smtp_port = 0
    if smtp_port not in SMTP_PUERTOS_PERMITIDOS and smtp_host.lower().find("gmail") >= 0:
        errores.append("Para Gmail usa puerto SMTP 587 (TLS) o 465 (SSL).")
    elif smtp_port < 1 or smtp_port > 65535:
        errores.append("Puerto SMTP debe estar entre 1 y 65535.")

    # Modo pruebas: email de pruebas obligatorio y válido
    modo_pruebas = (data.get("modo_pruebas") or "true").lower() == "true"
    if modo_pruebas:
        email_pruebas = (data.get("email_pruebas") or "").strip()
        if not email_pruebas:
            errores.append("En modo Pruebas el correo de pruebas es obligatorio.")
        elif not _validar_formato_email(email_pruebas):
            errores.append("El email de pruebas no tiene formato válido.")

    # tickets_notify_emails: si viene, cada uno debe ser email válido
    tickets_emails = (data.get("tickets_notify_emails") or "").strip()
    if tickets_emails:
        ok, res = validar_emails_lista(tickets_emails)
        if not ok:
            errores.extend(res if isinstance(res, list) else [str(res)])

    # IMAP opcional: si se envía host/usuario, validar puerto y formato usuario
    imap_host = (data.get("imap_host") or "").strip()
    imap_user = (data.get("imap_user") or "").strip()
    if imap_host or imap_user:
        try:
            imap_port = int(data.get("imap_port") or 993)
        except (TypeError, ValueError):
            imap_port = 0
        if imap_port not in IMAP_PUERTOS_PERMITIDOS and imap_host.lower().find("gmail") >= 0:
            errores.append("Para Gmail IMAP usa puerto 993 (SSL) o 143 (STARTTLS).")
        elif imap_port < 1 or imap_port > 65535:
            errores.append("Puerto IMAP debe estar entre 1 y 65535.")
        if imap_user and not _validar_formato_email(imap_user):
            errores.append("El usuario IMAP no tiene formato de email válido.")

    return (len(errores) == 0, errores)
