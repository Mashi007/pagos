"""
Endpoints de configuraciÃ³n de email (SMTP + IMAP).
GET/PUT /configuracion/email/configuracion, GET /configuracion/email/estado,
POST /configuracion/email/probar, POST /configuracion/email/probar-imap.
PolÃ­ticas Gmail: SMTP (enviar) 587/465, IMAP (recibir) 993 SSL o 143 STARTTLS, App Password.
tickets_notify_emails: contactos prestablecidos para notificaciÃ³n automÃ¡tica de tickets CRM.
La configuraciÃ³n se persiste en la tabla configuracion (clave=email_config) para que se actualice
y sobreviva reinicios y mÃºltiples workers (p. ej. Render).
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

# Stub en memoria (SMTP + IMAP + tickets). Con BD persistir en tabla de configuraciÃ³n.
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
    "tickets_notify_emails": "",  # Contactos prestablecidos: emails separados por coma para notificaciÃ³n de tickets
}


def _sync_stub_from_settings() -> None:
    """Rellena el stub con valores de .env cuando el usuario no ha guardado desde la UI (smtp_user vacÃ­o)."""
    if not _email_config_stub.get("smtp_user") and getattr(settings, "SMTP_USER", None):
        _email_config_stub["smtp_host"] = getattr(settings, "SMTP_HOST", None) or "smtp.gmail.com"
        _email_config_stub["smtp_port"] = str(getattr(settings, "SMTP_PORT", None) or 587)
        _email_config_stub["smtp_user"] = settings.SMTP_USER or ""
        _email_config_stub["from_email"] = getattr(settings, "SMTP_FROM_EMAIL", None) or settings.SMTP_USER or ""
        _email_config_stub["tickets_notify_emails"] = getattr(settings, "TICKETS_NOTIFY_EMAIL", None) or ""


def _load_email_config_from_db(db: Session) -> None:
    """Carga la configuraciÃ³n de email desde la tabla configuracion y la fusiona en el stub."""
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
        raise


@router.get("/configuracion")
def get_email_configuracion(db: Session = Depends(get_db)):
    """Devuelve la configuraciÃ³n de email (SMTP + IMAP + contactos tickets). No expone contraseÃ±as en texto plano."""
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
    """No sobrescribir la contraseÃ±a real con el valor enmascarado que envÃ­a el frontend."""
    if v is None or not isinstance(v, str):
        return True
    s = (v or "").strip()
    return s == "" or s == "***"


@router.put("/configuracion")
def put_email_configuracion(payload: EmailConfigUpdate = Body(...), db: Session = Depends(get_db)):
    """Actualiza configuraciÃ³n SMTP, IMAP y contactos para notificaciÃ³n de tickets. Persiste en BD."""
    _load_email_config_from_db(db)
    data = payload.model_dump(exclude_none=True)
    for k, v in data.items():
        if k not in _email_config_stub:
            continue
        if k in ("smtp_password", "imap_password") and _is_password_masked(v):
            continue
        _email_config_stub[k] = v
    update_from_api(_email_config_stub)
    _persist_email_config(db)
    logger.info("ConfiguraciÃ³n email actualizada y persistida en BD (campos: %s)", list(data.keys()))
    return {
        "message": "ConfiguraciÃ³n guardada",
        "vinculacion_confirmada": False,
        "mensaje_vinculacion": "Guarda la configuraciÃ³n y verifica la conexiÃ³n.",
        "requiere_app_password": False,
    }


@router.get("/estado")
def get_email_estado(db: Session = Depends(get_db)):
    """Estado de la configuraciÃ³n de email (para el frontend)."""
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
        problemas.append("Falta contraseÃ±a de aplicaciÃ³n (Gmail requiere App Password)")
    # No marcar conexion_smtp.success = True solo por tener campos; eso confunde si la contraseÃ±a es incorrecta.
    # La conexiÃ³n real se verifica con POST /probar (Enviar Email de Prueba).
    mensaje_estado = (
        "Datos completos. Usa 'Enviar Email de Prueba' para verificar la conexiÃ³n con Gmail."
        if configurada
        else "Completa SMTP y, si usas Gmail, contraseÃ±a de aplicaciÃ³n."
    )
    return {
        "configurada": configurada,
        "mensaje": mensaje_estado,
        "problemas": problemas,
        "conexion_smtp": {
            "success": False,
            "message": "Usa 'Enviar Email de Prueba' para verificar la conexiÃ³n." if configurada else None,
        },
        "modo_pruebas": (cfg.get("modo_pruebas") or "true").lower() == "true",
        "email_pruebas": cfg.get("email_pruebas") or None,
    }


class ProbarEmailRequest(BaseModel):
    email_destino: Optional[str] = None
    email_cc: Optional[str] = None
    subject: Optional[str] = None
    mensaje: Optional[str] = None

def _destino_prueba(cfg: dict[str, Any], payload: ProbarEmailRequest) -> str:
    """Destino del email de prueba: en modo pruebas usa email_pruebas; si no, el del payload."""
    modo_pruebas = (cfg.get("modo_pruebas") or "true").lower() == "true"
    if modo_pruebas and (cfg.get("email_pruebas") or "").strip():
        return (cfg["email_pruebas"] or "").strip()
    if (payload.email_destino or "").strip():
        return payload.email_destino.strip()
    return ""


@router.post(
    "/probar",
    summary="EnvÃ­a un email de prueba por SMTP con la configuraciÃ³n guardada.",
)
def post_email_probar(payload: ProbarEmailRequest = Body(...), db: Session = Depends(get_db)):
    """EnvÃ­a un correo de prueba por SMTP (usa config persistida en BD). En modo pruebas redirige a email_pruebas."""
    _load_email_config_from_db(db)
    _sync_stub_from_settings()
    from app.core.email_config_holder import sync_from_db
    from app.core.email import send_email

    sync_from_db()
    cfg = _email_config_stub
    if not all([cfg.get("smtp_host"), (cfg.get("smtp_user") or "").strip()]):
        raise HTTPException(
            status_code=400,
            detail="Configura servidor SMTP y usuario antes de enviar la prueba.",
        )
    if not cfg.get("smtp_password") or (cfg.get("smtp_password") or "").strip() in ("", "***"):
        raise HTTPException(
            status_code=400,
            detail="Falta contraseÃ±a SMTP (Gmail requiere ContraseÃ±a de aplicaciÃ³n). GuÃ¡rdala en ConfiguraciÃ³n y vuelve a probar.",
        )

    destino = _destino_prueba(cfg, payload)
    if not destino or "@" not in destino:
        raise HTTPException(
            status_code=400,
            detail="Indica un email de destino o activa Modo Pruebas y configura el Email de Pruebas.",
        )

    subject = (payload.subject or "").strip() or "Prueba de email - RapiCredit"
    body = (payload.mensaje or "").strip() or "Este es un correo de prueba enviado desde la configuraciÃ³n de email."
    recipients = [destino]
    if payload.email_cc and (payload.email_cc or "").strip():
        recipients.append(payload.email_cc.strip())
    ok, error_msg = send_email(to_emails=recipients, subject=subject, body_text=body)
    if not ok:
        # Devolver 200 con success=false para que el frontend muestre el mensaje sin tratar como error de red (502)
        logger.warning("Email de prueba fallÃ³: %s", error_msg)
        return {
            "success": False,
            "mensaje": error_msg or "No se pudo enviar el correo. Revisa servidor SMTP, puerto (587 o 465), TLS y contraseÃ±a de aplicaciÃ³n.",
            "email_destino": destino,
        }
    logger.info("Email de prueba enviado a %s", destino)
    return {
        "success": True,
        "mensaje": "Correo de prueba enviado correctamente.",
        "email_destino": destino,
    }


class ProbarImapRequest(BaseModel):
    """Opcional: envÃ­a la config IMAP del formulario para probar sin guardar antes."""
    imap_host: Optional[str] = None
    imap_port: Optional[str] = None
    imap_user: Optional[str] = None
    imap_password: Optional[str] = None
    imap_use_ssl: Optional[str] = None


@router.post(
    "/probar-imap",
    summary="[Stub] Prueba configuraciÃ³n IMAP; acepta config en body o usa la persistida en BD.",
)
def post_email_probar_imap(payload: ProbarImapRequest = Body(...), db: Session = Depends(get_db)):
    """Prueba de conexiÃ³n IMAP. Si el body trae imap_host, imap_user e imap_password, usa esos; si no, usa la config de BD. Stub: no abre conexiÃ³n real."""
    cfg: dict[str, Any]
    if (
        (payload.imap_host or "").strip()
        and (payload.imap_user or "").strip()
        and (payload.imap_password or "").strip()
        and (payload.imap_password or "").strip() != "***"
    ):
        cfg = {
            "imap_host": (payload.imap_host or "").strip(),
            "imap_port": (payload.imap_port or "993").strip(),
            "imap_user": (payload.imap_user or "").strip(),
            "imap_password": (payload.imap_password or "").strip(),
            "imap_use_ssl": (payload.imap_use_ssl or "true").strip().lower(),
        }
    else:
        _load_email_config_from_db(db)
        cfg = _email_config_stub

    imap_ok = bool(
        cfg.get("imap_host") and cfg.get("imap_user") and cfg.get("imap_password")
        and (cfg.get("imap_password") != "***")
    )
    if not imap_ok:
        raise HTTPException(
            status_code=400,
            detail="Configura imap_host, imap_user e imap_password (ContraseÃ±a de AplicaciÃ³n para Gmail) antes de probar IMAP.",
        )
    return {
        "success": True,
        "mensaje": "ConfiguraciÃ³n IMAP vÃ¡lida. Implementa conexiÃ³n IMAP real en el backend para verificar conexiÃ³n.",
    }

