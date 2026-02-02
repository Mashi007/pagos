"""
Endpoints de configuración de email (SMTP + IMAP).
GET/PUT /configuracion/email/configuracion, GET /configuracion/email/estado,
POST /configuracion/email/probar, POST /configuracion/email/probar-imap.
Políticas Gmail: SMTP (enviar) 587/465, IMAP (recibir) 993 SSL o 143 STARTTLS, App Password.
tickets_notify_emails: contactos prestablecidos para notificación automática de tickets CRM.
La configuración se persiste en la tabla configuracion (clave=email_config) para que se actualice
y sobreviva reinicios y múltiples workers (p. ej. Render).
Ref: https://support.google.com/mail/answer/7126229
"""
import json
import logging
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.email_config_holder import update_from_api
from app.models.configuracion import Configuracion

logger = logging.getLogger(__name__)
router = APIRouter()

CLAVE_EMAIL_CONFIG = "email_config"

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


def _load_email_config_from_db(db: Session) -> None:
    """Carga la configuración de email desde la tabla configuracion y la fusiona en el stub."""
    try:
        row = db.get(Configuracion, CLAVE_EMAIL_CONFIG)
        if row and row.valor:
            data = json.loads(row.valor)
            if isinstance(data, dict):
                for k, v in data.items():
                    if k in _email_config_stub and v is not None:
                        _email_config_stub[k] = v
    except Exception as e:
        logger.warning("No se pudo cargar config email desde BD: %s", e)


def _persist_email_config(db: Session) -> None:
    """Guarda el stub actual en la tabla configuracion para que persista entre reinicios y workers."""
    try:
        payload = json.dumps(_email_config_stub)
        row = db.get(Configuracion, CLAVE_EMAIL_CONFIG)
        if row:
            row.valor = payload
        else:
            db.add(Configuracion(clave=CLAVE_EMAIL_CONFIG, valor=payload))
        db.commit()
    except Exception as e:
        logger.exception("Error persistiendo config email en BD: %s", e)
        db.rollback()


@router.get("/configuracion")
def get_email_configuracion(db: Session = Depends(get_db)):
    """Devuelve la configuración de email (SMTP + IMAP + contactos tickets). No expone contraseñas en texto plano."""
    _load_email_config_from_db(db)
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


def _is_password_masked(v: str) -> bool:
    """No sobrescribir la contraseña real con el valor enmascarado que envía el frontend."""
    if v is None or not isinstance(v, str):
        return True
    s = (v or "").strip()
    return s == "" or s == "***"


@router.put("/configuracion")
def put_email_configuracion(payload: EmailConfigUpdate = Body(...), db: Session = Depends(get_db)):
    """Actualiza configuración SMTP, IMAP y contactos para notificación de tickets. Persiste en BD."""
    data = payload.model_dump(exclude_none=True)
    for k, v in data.items():
        if k not in _email_config_stub:
            continue
        if k in ("smtp_password", "imap_password") and _is_password_masked(v):
            continue
        _email_config_stub[k] = v
    update_from_api(_email_config_stub)
    _persist_email_config(db)
    logger.info("Configuración email actualizada y persistida en BD (campos: %s)", list(data.keys()))
    return {
        "message": "Configuración guardada",
        "vinculacion_confirmada": False,
        "mensaje_vinculacion": "Guarda la configuración y verifica la conexión.",
        "requiere_app_password": False,
    }


@router.get("/estado")
def get_email_estado(db: Session = Depends(get_db)):
    """Estado de la configuración de email (para el frontend)."""
    _load_email_config_from_db(db)
    _sync_stub_from_settings()
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


@router.post(
    "/probar",
    summary="[Stub] Prueba de envío SMTP; registra la petición pero no envía correo real.",
)
def post_email_probar(payload: ProbarEmailRequest = Body(...), db: Session = Depends(get_db)):
    """Prueba de envío SMTP (usa config persistida en BD). Stub: no envía correo real."""
    _load_email_config_from_db(db)
    return {
        "mensaje": "Prueba de envío registrada. Implementa envío SMTP en el backend para enviar realmente.",
        "email_destino": payload.email_destino or "",
    }


class ProbarImapRequest(BaseModel):
    pass


@router.post(
    "/probar-imap",
    summary="[Stub] Prueba configuración IMAP; no abre conexión real al servidor.",
)
def post_email_probar_imap(payload: ProbarImapRequest = Body(...), db: Session = Depends(get_db)):
    """Prueba de conexión IMAP (usa config persistida en BD). Stub: no verifica conexión real."""
    _load_email_config_from_db(db)
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
