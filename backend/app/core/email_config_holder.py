"""
Holder de configuración de email en tiempo de ejecución.
Usado por core/email.py para enviar (SMTP) y por tickets para destinos de notificación.
La API configuracion/email actualiza este holder al guardar; si no se ha guardado, se usan settings (.env).
"""
from typing import Any, List, Optional

from app.core.config import settings

# Config actual: smtp_*, from_email, from_name, tickets_notify_emails (str, emails separados por coma)
_current: dict[str, Any] = {}


def init_from_settings() -> None:
    """Inicializa el holder desde settings (.env) para que el envío funcione sin pasar por la UI."""
    _current["smtp_host"] = getattr(settings, "SMTP_HOST", None) or ""
    _current["smtp_port"] = str(getattr(settings, "SMTP_PORT", None) or 587)
    _current["smtp_user"] = getattr(settings, "SMTP_USER", None) or ""
    _current["smtp_password"] = getattr(settings, "SMTP_PASSWORD", None) or ""
    _current["from_email"] = getattr(settings, "SMTP_FROM_EMAIL", None) or _current.get("smtp_user") or ""
    _current["from_name"] = "RapiCredit"
    _current["tickets_notify_emails"] = getattr(settings, "TICKETS_NOTIFY_EMAIL", None) or ""


def get_smtp_config() -> dict[str, Any]:
    """Devuelve la config SMTP actual (holder o settings)."""
    if _current.get("smtp_user"):
        return {
            "smtp_host": _current.get("smtp_host") or "",
            "smtp_port": int(_current.get("smtp_port") or 587),
            "smtp_user": _current.get("smtp_user") or "",
            "smtp_password": _current.get("smtp_password") or "",
            "from_email": _current.get("from_email") or _current.get("smtp_user") or "",
            "from_name": _current.get("from_name") or "RapiCredit",
        }
    return {
        "smtp_host": getattr(settings, "SMTP_HOST", None) or "",
        "smtp_port": getattr(settings, "SMTP_PORT", None) or 587,
        "smtp_user": getattr(settings, "SMTP_USER", None) or "",
        "smtp_password": getattr(settings, "SMTP_PASSWORD", None) or "",
        "from_email": getattr(settings, "SMTP_FROM_EMAIL", None) or getattr(settings, "SMTP_USER", None) or "",
        "from_name": "RapiCredit",
    }


def get_tickets_notify_emails() -> List[str]:
    """Lista de emails a los que notificar cuando se crea/actualiza un ticket (contactos prestablecidos)."""
    raw = _current.get("tickets_notify_emails") or getattr(settings, "TICKETS_NOTIFY_EMAIL", None) or ""
    return [e.strip() for e in raw.split(",") if e.strip()]


def update_from_api(data: dict[str, Any]) -> None:
    """Actualiza el holder desde la API de configuración (PUT /configuracion/email/configuracion)."""
    for k in ("smtp_host", "smtp_port", "smtp_user", "smtp_password", "from_email", "from_name", "tickets_notify_emails"):
        if k in data and data[k] is not None:
            _current[k] = data[k]
    if "smtp_port" in data and data["smtp_port"] is not None:
        _current["smtp_port"] = str(data["smtp_port"])
