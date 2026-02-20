"""
Endpoints de configuracion de email (SMTP + IMAP).
GET/PUT /configuracion/email/configuracion, GET /configuracion/email/estado,
POST /configuracion/email/probar, POST /configuracion/email/probar-imap.
Politicas Gmail: SMTP (enviar) 587/465, IMAP (recibir) 993 SSL o 143 STARTTLS, App Password.
tickets_notify_emails: contactos prestablecidos para notificacion automatica de tickets CRM.
La configuracion se persiste en la tabla configuracion (clave=email_config) para que se actualice
y sobreviva reinicios y multiples workers (p. ej. Render).
Ref: https://support.google.com/mail/answer/7126229

Integracion con encriptacion:
- Campos sensibles (smtp_password, imap_password) se encriptan al guardar en BD
- Se desencriptan automaticamente al cargar desde BD
- Al devolver al API, se enmascaran (no se expone la contrasena)
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

# Stub en memoria (SMTP + IMAP + tickets). Con BD persistir en tabla de configuracion.
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
    "tickets_notify_emails": "",
}


def _sync_stub_from_settings() -> None:
    """Rellena el stub con valores de .env cuando el usuario no ha guardado desde la UI (smtp_user vacio)."""
    if not _email_config_stub.get("smtp_user") and getattr(settings, "SMTP_USER", None):
        _email_config_stub["smtp_host"] = getattr(settings, "SMTP_HOST", None) or "smtp.gmail.com"
        _email_config_stub["smtp_port"] = str(getattr(settings, "SMTP_PORT", None) or 587)
        _email_config_stub["smtp_user"] = settings.SMTP_USER or ""
        _email_config_stub["from_email"] = getattr(settings, "SMTP_FROM_EMAIL", None) or settings.SMTP_USER or ""
        _email_config_stub["tickets_notify_emails"] = getattr(settings, "TICKETS_NOTIFY_EMAIL", None) or ""


def _load_email_config_from_db(db: Session) -> None:
    """Carga la configuracion de email desde la tabla configuracion y la fusiona en el stub."""
    from app.core.email_config_holder import _decrypt_value_safe, SENSITIVE_FIELDS
    
    try:
        row = db.get(Configuracion, CLAVE_EMAIL_CONFIG)
        if row and row.valor:
            data = json.loads(row.valor)
            if isinstance(data, dict):
                for k, v in data.items():
                    if k in _email_config_stub and v is not None:
                        if k.endswith("_encriptado"):
                            base_field = k.replace("_encriptado", "")
                            if base_field in SENSITIVE_FIELDS:
                                try:
                                    encrypted_bytes = bytes.fromhex(v) if isinstance(v, str) else v
                                    decrypted = _decrypt_value_safe(encrypted_bytes)
                                    if decrypted:
                                        _email_config_stub[base_field] = decrypted
                                        continue
                                except Exception:
                                    pass
                        _email_config_stub[k] = v
    except Exception as e:
        logger.warning("No se pudo cargar config email desde BD: %s", e)


def _persist_email_config(db: Session) -> None:
    """Guarda el stub actual en la tabla configuracion para que persista entre reinicios y workers."""
    from app.core.email_config_holder import prepare_for_db_storage
    
    try:
        payload_data = prepare_for_db_storage(_email_config_stub)
        payload = json.dumps(payload_data)
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
    """Devuelve la configuracion de email (SMTP + IMAP + contactos tickets). No expone contrasenas en texto plano."""
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
    """No sobrescribir la contrasena real con el valor enmascarado que envia el frontend."""
    if v is None or not isinstance(v, str):
        return True
    s = (v or "").strip()
    return s == "" or s == "***"


@router.put("/configuracion")
def put_email_configuracion(payload: EmailConfigUpdate = Body(...), db: Session = Depends(get_db)):
    """Actualiza configuracion SMTP, IMAP y contactos para notificacion de tickets. Persiste en BD."""
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
    logger.info("Configuracion email actualizada y persistida en BD (campos: %s)", list(data.keys()))
    return {
        "message": "Configuracion guardada",
        "vinculacion_confirmada": False,
        "mensaje_vinculacion": "Guarda la configuracion y verifica la conexion.",
        "requiere_app_password": False,
    }


@router.get("/estado")
def get_email_estado(db: Session = Depends(get_db)):
    """Estado de la configuracion de email (para el frontend)."""
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
        problemas.append("Falta contrasena de aplicacion (Gmail requiere App Password)")
    mensaje_estado = (
        "Datos completos. Usa 'Enviar Email de Prueba' para verificar la conexion con Gmail."
        if configurada
        else "Completa SMTP y, si usas Gmail, contrasena de aplicacion."
    )
    return {
        "configurada": configurada,
        "mensaje": mensaje_estado,
        "problemas": problemas,
        "conexion_smtp": {
            "success": False,
            "message": "Usa 'Enviar Email de Prueba' para verificar la conexion." if configurada else None,
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
    """Destino del email de prueba: prioridad a los correos que el usuario pone manualmente en la interfaz."""
    if (payload.email_destino or "").strip():
        return payload.email_destino.strip()
    modo_pruebas = (cfg.get("modo_pruebas") or "true").lower() == "true"
    if modo_pruebas and (cfg.get("email_pruebas") or "").strip():
        return (cfg["email_pruebas"] or "").strip()
    return ""


@router.post(
    "/probar",
    summary="Envia un email de prueba por SMTP con la configuracion guardada.",
)
def post_email_probar(payload: ProbarEmailRequest = Body(...), db: Session = Depends(get_db)):
    """Envia un correo de prueba por SMTP (usa config persistida en BD). En modo pruebas redirige a email_pruebas."""
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
            detail="Falta contrasena SMTP (Gmail requiere Contrasena de aplicacion). Guardala en Configuracion y vuelve a probar.",
        )

    destino = _destino_prueba(cfg, payload)
    if not destino or "@" not in destino:
        raise HTTPException(
            status_code=400,
            detail="Indica un email de destino válido (ej: usuario@dominio.com) o activa Modo Pruebas y configura el Email de Pruebas.",
        )
    # Validar formato básico de email (evitar truncados como usuario@dominio.c)
    if "." not in destino.split("@")[-1] or len(destino.split("@")[-1].split(".")[-1]) < 2:
        raise HTTPException(
            status_code=400,
            detail=f"El email '{destino}' no tiene formato válido. Verifica que el dominio esté completo (ej: .com, .net).",
        )

    subject = (payload.subject or "").strip() or "Prueba de email - RapiCredit"
    body = (payload.mensaje or "").strip() or "Este es un correo de prueba enviado desde la configuracion de email."
    recipients = [destino]
    if payload.email_cc and (payload.email_cc or "").strip():
        recipients.append(payload.email_cc.strip())
    ok, error_msg = send_email(to_emails=recipients, subject=subject, body_text=body, respetar_destinos_manuales=True)
    if not ok:
        logger.warning("Email de prueba fallo: %s", error_msg)
        return {
            "success": False,
            "mensaje": error_msg or "No se pudo enviar el correo. Revisa servidor SMTP, puerto (587 o 465), TLS y contrasena de aplicacion.",
            "email_destino": destino,
        }
    logger.info("Email de prueba enviado a %s", destino)
    return {
        "success": True,
        "mensaje": "Correo de prueba enviado correctamente.",
        "email_destino": destino,
    }


class ProbarImapRequest(BaseModel):
    """Opcional: envia la config IMAP del formulario para probar sin guardar antes."""
    imap_host: Optional[str] = None
    imap_port: Optional[str] = None
    imap_user: Optional[str] = None
    imap_password: Optional[str] = None
    imap_use_ssl: Optional[str] = None


@router.post(
    "/probar-imap",
    summary="Prueba conexion IMAP real; acepta config en body o usa la persistida en BD.",
)
def post_email_probar_imap(payload: ProbarImapRequest = Body(...), db: Session = Depends(get_db)):
    """Prueba de conexion IMAP con verificacion real. Si el body trae imap_host, imap_user e imap_password, usa esos; si no, usa la config de BD."""
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
            detail="Configura imap_host, imap_user e imap_password (Contrasena de Aplicacion para Gmail) antes de probar IMAP.",
        )

    from app.core.email import test_imap_connection

    port = int(cfg.get("imap_port") or 993)
    use_ssl = (cfg.get("imap_use_ssl") or "true").lower() == "true"
    success, error_msg, folders = test_imap_connection(
        imap_host=cfg["imap_host"],
        imap_port=port,
        imap_user=cfg["imap_user"],
        imap_password=cfg["imap_password"],
        imap_use_ssl=use_ssl,
    )

    if success:
        logger.info("Prueba IMAP exitosa para %s en %s:%d", cfg["imap_user"], cfg["imap_host"], port)
        return {
            "success": True,
            "mensaje": error_msg or "Conexion IMAP exitosa.",
            "carpetas_encontradas": folders or [],
        }
    else:
        logger.warning("Prueba IMAP fallo para %s: %s", cfg["imap_user"], error_msg)
        return {
            "success": False,
            "mensaje": error_msg or "No se pudo conectar al servidor IMAP. Verifica host, puerto, usuario y contrasena.",
        }
