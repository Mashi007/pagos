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
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.email_config_holder import update_from_api
from app.core.email_phases import FASE_CONFIG_GUARDADO, log_phase
from app.models.configuracion import Configuracion
from app.api.v1.endpoints.email_config_validacion import validar_config_email_para_guardar

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
    "email_activo_notificaciones": "true",
    "email_activo_informe_pagos": "true",
    "email_activo_estado_cuenta": "true",
    "email_activo_finiquito": "true",
    "email_activo_cobros": "true",
    "email_activo_campanas": "true",
    "email_activo_tickets": "true",
    "email_activo_recibos": "true",
    "modo_pruebas_notificaciones": "false",
    "modo_pruebas_informe_pagos": "false",
    "modo_pruebas_estado_cuenta": "false",
    "modo_pruebas_finiquito": "false",
    "modo_pruebas_cobros": "false",
    "modo_pruebas_campanas": "false",
    "modo_pruebas_tickets": "false",
    "modo_pruebas_recibos": "false",
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
                    if k.endswith("_encriptado") and v is not None:
                        base_field = k.replace("_encriptado", "")
                        if base_field in _email_config_stub and base_field in SENSITIVE_FIELDS:
                            try:
                                encrypted_bytes = bytes.fromhex(v) if isinstance(v, str) else v
                                decrypted = _decrypt_value_safe(encrypted_bytes)
                                if decrypted:
                                    _email_config_stub[base_field] = decrypted
                            except Exception:
                                pass
                        continue
                    if k in _email_config_stub and v is not None:
                        _email_config_stub[k] = v
    except Exception as e:
        logger.warning("No se pudo cargar config email desde BD: %s", e)



# Claves globales que comparten stub y config version 2. Al guardar desde legacy, solo se fusionan estas.
_STUB_GLOBAL_KEYS = (
    "modo_pruebas", "email_pruebas", "emails_pruebas",
    "email_activo",     "email_activo_notificaciones", "email_activo_informe_pagos",
    "email_activo_estado_cuenta", "email_activo_finiquito", "email_activo_cobros", "email_activo_campanas", "email_activo_tickets",
    "email_activo_recibos",
    "modo_pruebas_notificaciones", "modo_pruebas_informe_pagos", "modo_pruebas_estado_cuenta",
    "modo_pruebas_finiquito", "modo_pruebas_cobros", "modo_pruebas_campanas", "modo_pruebas_tickets",
    "modo_pruebas_recibos",
    "tickets_notify_emails",
)

def _persist_email_config(db: Session) -> None:
    """Guarda el stub actual en la tabla configuracion para que persista entre reinicios y workers."""
    from app.core.email_config_holder import prepare_for_db_storage
    
    try:
        row = db.get(Configuracion, CLAVE_EMAIL_CONFIG)
        if row and row.valor:
            try:
                data = json.loads(row.valor)
                if isinstance(data, dict) and data.get("version") == 2 and "cuentas" in data:
                    for key in _STUB_GLOBAL_KEYS:
                        if key in _email_config_stub:
                            data[key] = _email_config_stub[key]
                    row.valor = json.dumps(data)
                    db.commit()
                    return
            except (json.JSONDecodeError, TypeError):
                pass
        payload_data = prepare_for_db_storage(_email_config_stub)
        payload = json.dumps(payload_data)
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
    email_activo_notificaciones: Optional[str] = None
    email_activo_informe_pagos: Optional[str] = None
    email_activo_estado_cuenta: Optional[str] = None
    email_activo_finiquito: Optional[str] = None
    email_activo_cobros: Optional[str] = None
    email_activo_campanas: Optional[str] = None
    email_activo_tickets: Optional[str] = None
    email_activo_recibos: Optional[str] = None
    modo_pruebas_notificaciones: Optional[str] = None
    modo_pruebas_informe_pagos: Optional[str] = None
    modo_pruebas_estado_cuenta: Optional[str] = None
    modo_pruebas_finiquito: Optional[str] = None
    modo_pruebas_cobros: Optional[str] = None
    modo_pruebas_campanas: Optional[str] = None
    modo_pruebas_tickets: Optional[str] = None
    modo_pruebas_recibos: Optional[str] = None
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
    password_skipped = False
    for k, v in data.items():
        if k not in _email_config_stub:
            continue
        if k in ("smtp_password", "imap_password") and _is_password_masked(v):
            password_skipped = True
            continue
        _email_config_stub[k] = v
    valido, errores = validar_config_email_para_guardar(_email_config_stub)
    if not valido:
        raise HTTPException(status_code=400, detail="; ".join(errores))
    update_from_api(_email_config_stub)
    _persist_email_config(db)
    log_phase(logger, FASE_CONFIG_GUARDADO, True, "config email guardada en BD", extra={"campos": list(data.keys())})
    logger.info("Configuracion email actualizada y persistida en BD (campos: %s)", list(data.keys()))
    resp = {
        "message": "Configuracion guardada",
        "vinculacion_confirmada": False,
        "mensaje_vinculacion": "Guarda la configuracion y verifica la conexion.",
        "requiere_app_password": False,
    }
    if password_skipped:
        resp["password_not_updated"] = True
        resp["mensaje_password"] = "La contraseña no se modificó (el campo tenía *** o vacío). Para cambiarla, reingrésala y guarda de nuevo."
    return resp


def _cuenta_tiene_smtp_usable(c: Any) -> bool:
    """True si la cuenta puede enviar: host, usuario y contraseña (texto o smtp_password_encriptado en JSON)."""
    if not isinstance(c, dict):
        return False
    host = (c.get("smtp_host") or "").strip()
    user = (c.get("smtp_user") or "").strip()
    if not host or not user:
        return False
    pw = (c.get("smtp_password") or "").strip()
    if pw and pw != "***":
        return True
    return bool(c.get("smtp_password_encriptado"))


def _smtp_configurada_desde_json_email(data: Optional[dict]) -> tuple[bool, list[str]]:
    """
    Considera configuracion version 2 (4 cuentas) ademas del formato legacy plano.
    Asi GET /estado no marca 'no configurado' cuando solo existe email_config v2 en BD.
    """
    if not data or not isinstance(data, dict):
        return False, ["No hay configuración de email en base de datos"]
    if data.get("version") == 2 and isinstance(data.get("cuentas"), list):
        if any(_cuenta_tiene_smtp_usable(c) for c in data["cuentas"]):
            return True, []
        return False, [
            "Ninguna cuenta tiene SMTP completo (servidor, usuario y contraseña). Revise Configuración → Email."
        ]
    host = (data.get("smtp_host") or "").strip()
    user = (data.get("smtp_user") or "").strip()
    pw = (data.get("smtp_password") or "").strip()
    has_pw = (pw and pw != "***") or bool(data.get("smtp_password_encriptado"))
    if host and user and has_pw:
        return True, []
    problemas: list[str] = []
    if not host:
        problemas.append("Falta servidor SMTP")
    if not user:
        problemas.append("Falta email de usuario")
    if not has_pw:
        problemas.append(
            "Falta contraseña (normal o de aplicación; en cuentas corporativas usa la contraseña normal)"
        )
    return False, problemas


@router.get("/estado")
def get_email_estado(db: Session = Depends(get_db)):
    """Estado SMTP para el frontend: soporta email_config version 2 (cuatro cuentas) y legacy."""
    _load_email_config_from_db(db)
    _sync_stub_from_settings()
    row = db.get(Configuracion, CLAVE_EMAIL_CONFIG)
    raw: Optional[dict] = None
    if row and row.valor:
        try:
            parsed = json.loads(row.valor)
            if isinstance(parsed, dict):
                raw = parsed
        except (json.JSONDecodeError, TypeError):
            raw = None

    configurada, problemas = _smtp_configurada_desde_json_email(raw)

    cfg = _email_config_stub
    if not configurada:
        stub_pw = cfg.get("smtp_password") or ""
        stub_ok = bool(
            (cfg.get("smtp_host") or "").strip()
            and (cfg.get("smtp_user") or "").strip()
            and str(stub_pw).strip()
            and str(stub_pw).strip() != "***"
        )
        if stub_ok:
            configurada = True
            problemas = []

    mensaje_estado = (
        "SMTP configurado (cuentas v2 o legado). Puede enviar correo de prueba."
        if configurada
        else "Complete SMTP en Configuración → Email (cuentas 1–4 o formato anterior)."
    )
    return {
        "configurada": configurada,
        "mensaje": mensaje_estado,
        "problemas": [] if configurada else problemas,
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
    # Opcional: misma cuenta SMTP que un servicio (p. ej. notificaciones, cuentas 3/4).
    # Por defecto cobros (Cuenta 1), comportamiento historico.
    servicio: Optional[str] = None
    tipo_tab: Optional[str] = None
    # Recibos: enviar muestra con HTML + PDF reales (primer cliente en ventana), solo a email_destino.
    recibos_prueba_datos_reales: bool = False
    fecha_caracas: Optional[str] = None
    recibos_html_plantilla: Optional[str] = Field(
        None,
        max_length=1_800_000,
        description="HTML crudo del cuerpo Recibos (editor admin). Vacío = archivo en disco.",
    )


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
    """Envia un correo de prueba por SMTP (config persistida en BD). Con email_config v2 la cuenta depende de servicio/tipo_tab."""
    _load_email_config_from_db(db)
    _sync_stub_from_settings()
    from app.core.email_config_holder import sync_from_db, get_smtp_config
    from app.core.email import send_email

    sync_from_db()
    raw_svc = (payload.servicio or "cobros").strip().lower()
    if raw_svc not in (
        "cobros",
        "notificaciones",
        "estado_cuenta",
        "tickets",
        "campanas",
        "informe_pagos",
        "recibos",
    ):
        raw_svc = "cobros"
    tipo_tab = (payload.tipo_tab or "").strip() or None
    cfg_send = get_smtp_config(servicio=raw_svc, tipo_tab=tipo_tab)
    if not all([cfg_send.get("smtp_host"), (cfg_send.get("smtp_user") or "").strip()]):
        raise HTTPException(
            status_code=400,
            detail="Configura servidor SMTP y usuario antes de enviar la prueba.",
        )
    if not cfg_send.get("smtp_password") or (cfg_send.get("smtp_password") or "").strip() in ("", "***"):
        raise HTTPException(
            status_code=400,
            detail="Falta contraseña SMTP. En cuentas corporativas/Google Workspace usa tu contraseña normal; en Gmail personal puede requerir Contraseña de aplicación.",
        )

    destino = _destino_prueba(_email_config_stub, payload)
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

    if raw_svc == "recibos" and payload.recibos_prueba_datos_reales:
        from app.services.cuota_estado import hoy_negocio, parse_fecha_referencia_negocio
        from app.services.recibos_conciliacion_email_job import enviar_correo_prueba_recibos_datos_reales

        raw_fc = (payload.fecha_caracas or "").strip()
        try:
            d = parse_fecha_referencia_negocio(raw_fc) if raw_fc else hoy_negocio()
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        if d is None:
            d = hoy_negocio()
        ov = (payload.recibos_html_plantilla or "").strip()
        out = enviar_correo_prueba_recibos_datos_reales(
            db,
            email_destino=destino,
            fecha_dia=d,
            html_plantilla_override=ov or None,
        )
        if not out.get("success"):
            logger.warning("Recibos prueba datos reales: %s", out.get("mensaje"))
            return {
                "success": False,
                "mensaje": out.get("mensaje") or "No se pudo enviar la muestra Recibos.",
                "email_destino": destino,
                "detalle": {k: v for k, v in out.items() if k not in ("success", "mensaje")},
            }
        logger.info("Recibos prueba datos reales enviada a %s", destino)
        return {
            "success": True,
            "mensaje": out.get("mensaje") or "Muestra Recibos enviada.",
            "email_destino": destino,
            "detalle": {k: v for k, v in out.items() if k not in ("success", "mensaje")},
        }

    subject = (payload.subject or "").strip() or "Prueba de email - RapiCredit"
    body = (payload.mensaje or "").strip() or "Este es un correo de prueba enviado desde la configuracion de email."
    if "{{LOGO_URL}}" in body:
        try:
            from app.core.email import _logo_url_for_email
            body = body.replace("{{LOGO_URL}}", _logo_url_for_email())
        except Exception:
            body = body.replace("{{LOGO_URL}}", "https://rapicredit.onrender.com/pagos/logos/rapicredit-public.png")
    recipients = [destino]
    if payload.email_cc and (payload.email_cc or "").strip():
        recipients.append(payload.email_cc.strip())
    ok, error_msg = send_email(
        to_emails=recipients,
        subject=subject,
        body_text=body,
        respetar_destinos_manuales=True,
        servicio=raw_svc,
        tipo_tab=tipo_tab,
    )
    if not ok:
        logger.warning("Email de prueba fallo: %s", error_msg)
        return {
            "success": False,
            "mensaje": error_msg or "No se pudo enviar el correo. Revisa servidor SMTP, puerto (587 o 465), TLS y contraseña.",
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
            detail="Configura imap_host, imap_user e imap_password antes de probar IMAP (contraseña normal en cuentas corporativas).",
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
