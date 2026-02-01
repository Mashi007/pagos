"""
Endpoints de configuración de email (SMTP + IMAP).
GET/PUT /configuracion/email/configuracion, GET /configuracion/email/estado,
POST /configuracion/email/probar, POST /configuracion/email/probar-imap.
Políticas Gmail: SMTP (enviar) 587/465, IMAP (recibir) 993 SSL o 143 STARTTLS, App Password.
tickets_notify_emails: contactos prestablecidos para notificación automática de tickets CRM.
Ref: https://support.google.com/mail/answer/7126229
"""
from typing import Any, Optional

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.core.email_config_holder import update_from_api

router = APIRouter()

# Stub en memoria (SMTP + IMAP + tickets). Con BD persistir en tabla de configuración.
_email_config_stub: dict[str, Any] = {
    "smtp_host": "smtp.gmail.com",
    "smtp_port": "587",
    "smtp_user": "",
    "smtp_password": "",
    "from_email": "",
    "from_name": "RapiCredit",
    "smtp_use_tls": "true",
    "modo_pruebas": "true",
    "email_pruebas": "",
    "email_activo": "true",
    "imap_host": "",
    "imap_port": "993",
    "imap_user": "",
    "imap_password": "",
    "imap_use_ssl": "true",
    "tickets_notify_emails": "",  # Contactos prestablecidos: emails separados por coma para notificación de tickets
}


def _sync_stub_from_settings() -> None:
    """Rellena el stub con valores de .env cuando el usuario no ha guardado desde la UI (smtp_user vacío)."""
    if not _email_config_stub.get("smtp_user") and getattr(settings, "SMTP_USER", None):
        _email_config_stub["smtp_host"] = getattr(settings, "SMTP_HOST", None) or "smtp.gmail.com"
        _email_config_stub["smtp_port"] = str(getattr(settings, "SMTP_PORT", None) or 587)
        _email_config_stub["smtp_user"] = settings.SMTP_USER or ""
        _email_config_stub["from_email"] = getattr(settings, "SMTP_FROM_EMAIL", None) or settings.SMTP_USER or ""
        _email_config_stub["tickets_notify_emails"] = getattr(settings, "TICKETS_NOTIFY_EMAIL", None) or ""


@router.get("/configuracion")
def get_email_configuracion():
    """Devuelve la configuración de email (SMTP + IMAP + contactos tickets). No expone contraseñas en texto plano."""
    _sync_stub_from_settings()
    out = _email_config_stub.copy()
    if out.get("smtp_password"):
        out["smtp_password"] = "***"
    if out.get("imap_password"):
        out["imap_password"] = "***"
    return out


class EmailConfigUpdate(BaseModel):
    smtp_host: Optional[str] = None
    smtp_port: Optional[str] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    from_email: Optional[str] = None
    from_name: Optional[str] = None
    smtp_use_tls: Optional[str] = None
    modo_pruebas: Optional[str] = None
    email_pruebas: Optional[str] = None
    email_activo: Optional[str] = None
    imap_host: Optional[str] = None
    imap_port: Optional[str] = None
    imap_user: Optional[str] = None
    imap_password: Optional[str] = None
    imap_use_ssl: Optional[str] = None
    tickets_notify_emails: Optional[str] = None


@router.put("/configuracion")
def put_email_configuracion(payload: EmailConfigUpdate = Body(...)):
    """Actualiza configuración SMTP, IMAP y contactos para notificación de tickets."""
    data = payload.model_dump(exclude_none=True)
    for k, v in data.items():
        if k in _email_config_stub:
            if k in ("smtp_password", "imap_password") and v == "":
                continue
            _email_config_stub[k] = v
    update_from_api(_email_config_stub)
    return {
        "message": "Configuración guardada",
        "vinculacion_confirmada": False,
        "mensaje_vinculacion": "Guarda la configuración y verifica la conexión.",
        "requiere_app_password": False,
    }


@router.get("/estado")
def get_email_estado():
    """Estado de la configuración de email (para el frontend)."""
    cfg = _email_config_stub
    configurada = bool(
        cfg.get("smtp_host") and cfg.get("smtp_user") and cfg.get("smtp_password")
    )
    problemas = []
    if not cfg.get("smtp_host"):
        problemas.append("Falta servidor SMTP")
    if not cfg.get("smtp_user"):
        problemas.append("Falta email de usuario")
    if not cfg.get("smtp_password") or cfg.get("smtp_password") == "***":
        problemas.append("Falta contraseña de aplicación (Gmail requiere App Password)")
    return {
        "configurada": configurada,
        "mensaje": "Configuración correcta" if configurada else "Completa SMTP y, si usas Gmail, contraseña de aplicación.",
        "problemas": problemas,
        "conexion_smtp": {"success": configurada, "message": None},
        "modo_pruebas": (cfg.get("modo_pruebas") or "true").lower() == "true",
        "email_pruebas": cfg.get("email_pruebas") or None,
    }


class ProbarEmailRequest(BaseModel):
    email_destino: Optional[str] = None
    subject: Optional[str] = None
    mensaje: Optional[str] = None


@router.post("/probar")
def post_email_probar(payload: ProbarEmailRequest = Body(...)):
    """Prueba de envío SMTP (stub: no envía realmente sin implementación)."""
    return {
        "mensaje": "Prueba de envío registrada. Implementa envío SMTP en el backend para enviar realmente.",
        "email_destino": payload.email_destino or "",
    }


class ProbarImapRequest(BaseModel):
    pass


@router.post("/probar-imap")
def post_email_probar_imap(payload: ProbarImapRequest = Body(...)):
    """Prueba de conexión IMAP (stub: verifica que haya host/user/password configurados)."""
    cfg = _email_config_stub
    imap_ok = bool(
        cfg.get("imap_host") and cfg.get("imap_user") and cfg.get("imap_password")
        and (cfg.get("imap_password") != "***")
    )
    if not imap_ok:
        raise HTTPException(
            status_code=400,
            detail="Configura imap_host, imap_user e imap_password (Contraseña de Aplicación para Gmail) antes de probar IMAP.",
        )
    return {
        "success": True,
        "mensaje": "Configuración IMAP válida. Implementa conexión IMAP real en el backend para verificar conexión.",
    }
