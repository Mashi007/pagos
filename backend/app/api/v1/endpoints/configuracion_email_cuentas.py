"""
Endpoints para configuracion de 4 cuentas de email.
GET/PUT /configuracion/email/cuentas devuelven/aceptan { version: 2, cuentas: [c1,c2,c3,c4], asignacion }.
Cuenta 1 = Cobros, 2 = Estado de cuenta, 3 y 4 = Notificaciones (por pestaña).
"""
import json
import logging
from typing import Any, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.email_config_holder import (
    CLAVE_EMAIL_CONFIG,
    SENSITIVE_FIELDS,
    prepare_for_db_storage,
    update_from_api,
)
from app.core.email_cuentas import (
    NUM_CUENTAS,
    ASIGNACION_DEFAULT,
    cuenta_vacia,
    migrar_config_v1_a_v2,
)
from app.models.configuracion import Configuracion
from app.api.v1.endpoints.email_config_validacion import validar_config_email_para_guardar

logger = logging.getLogger(__name__)
router = APIRouter()


def _mask_cuenta(c: dict) -> dict:
    """Copia la cuenta enmascarando contraseñas y sin exponer campos _encriptado."""
    out = {k: v for k, v in c.items() if not k.endswith("_encriptado")}
    for f in SENSITIVE_FIELDS:
        if out.get(f):
            out[f] = "***"
    return out


def _load_raw_from_db(db) -> Optional[dict]:
    row = db.get(Configuracion, CLAVE_EMAIL_CONFIG)
    if not row or not row.valor:
        return None
    try:
        return json.loads(row.valor)
    except Exception:
        return None


@router.get("/cuentas")
def get_email_cuentas(db: Session = Depends(get_db)):
    """Devuelve la configuracion de 4 cuentas y asignacion. Contrasenas enmascaradas."""
    data = _load_raw_from_db(db)
    if not data:
        out = {
            "version": 2,
            "cuentas": [cuenta_vacia() for _ in range(NUM_CUENTAS)],
            "asignacion": dict(ASIGNACION_DEFAULT),
        }
        for c in out["cuentas"]:
            _mask_cuenta(c)
        return out
    if data.get("version") == 2 and "cuentas" in data:
        cuentas = list(data["cuentas"])
        for i, c in enumerate(cuentas):
            if isinstance(c, dict):
                cuentas[i] = _mask_cuenta(dict(c))
        return {
            "version": 2,
            "cuentas": cuentas,
            "asignacion": data.get("asignacion") or ASIGNACION_DEFAULT,
            "modo_pruebas": data.get("modo_pruebas", "true"),
            "email_pruebas": data.get("email_pruebas", ""),
            "email_activo": data.get("email_activo", "true"),
            "email_activo_notificaciones": data.get("email_activo_notificaciones", "true"),
            "email_activo_estado_cuenta": data.get("email_activo_estado_cuenta", "true"),
            "email_activo_cobros": data.get("email_activo_cobros", "true"),
            "tickets_notify_emails": data.get("tickets_notify_emails", ""),
        }
    migrated = migrar_config_v1_a_v2(data)
    cuentas = list(migrated["cuentas"])
    for i, c in enumerate(cuentas):
        if isinstance(c, dict):
            cuentas[i] = _mask_cuenta(dict(c))
    return {
        "version": 2,
        "cuentas": cuentas,
        "asignacion": migrated.get("asignacion") or ASIGNACION_DEFAULT,
        "modo_pruebas": migrated.get("modo_pruebas", "true"),
        "email_pruebas": migrated.get("email_pruebas", ""),
        "email_activo": migrated.get("email_activo", "true"),
        "email_activo_notificaciones": migrated.get("email_activo_notificaciones", "true"),
        "email_activo_estado_cuenta": migrated.get("email_activo_estado_cuenta", "true"),
        "email_activo_cobros": migrated.get("email_activo_cobros", "true"),
        "tickets_notify_emails": migrated.get("tickets_notify_emails", ""),
    }


class CuentaEmail(BaseModel):
    smtp_host: Optional[str] = None
    smtp_port: Optional[str] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    from_email: Optional[str] = None
    from_name: Optional[str] = None
    smtp_use_tls: Optional[str] = None
    imap_host: Optional[str] = None
    imap_port: Optional[str] = None
    imap_user: Optional[str] = None
    imap_password: Optional[str] = None
    imap_use_ssl: Optional[str] = None


class EmailCuentasUpdate(BaseModel):
    cuentas: List[CuentaEmail]
    asignacion: Optional[dict] = None
    modo_pruebas: Optional[str] = None
    email_pruebas: Optional[str] = None
    email_activo: Optional[str] = None
    email_activo_notificaciones: Optional[str] = None
    email_activo_estado_cuenta: Optional[str] = None
    email_activo_cobros: Optional[str] = None
    tickets_notify_emails: Optional[str] = None


def _is_password_masked(v: Any) -> bool:
    if v is None or not isinstance(v, str):
        return True
    s = (v or "").strip()
    return s in ("", "***")


@router.put("/cuentas")
def put_email_cuentas(payload: EmailCuentasUpdate = Body(...), db: Session = Depends(get_db)):
    """Guarda las 4 cuentas y la asignacion. Encripta contrasenas en BD."""
    cuentas = payload.cuentas or []
    if len(cuentas) < NUM_CUENTAS:
        cuentas = list(cuentas) + [{} for _ in range(NUM_CUENTAS - len(cuentas))]
    cuentas = cuentas[:NUM_CUENTAS]
    asignacion = payload.asignacion or ASIGNACION_DEFAULT
    if "notificaciones_tab" not in asignacion:
        asignacion = dict(asignacion)
        asignacion["notificaciones_tab"] = ASIGNACION_DEFAULT["notificaciones_tab"]

    cuentas_dict: List[dict] = []
    for i, c in enumerate(cuentas):
        d = c.model_dump(exclude_none=True) if hasattr(c, "model_dump") else dict(c)
        base = cuenta_vacia()
        for k, v in d.items():
            if k in base and v is not None:
                if k in ("smtp_password", "imap_password") and _is_password_masked(v):
                    continue
                base[k] = v
        cuentas_dict.append(base)

    for i, c in enumerate(cuentas_dict):
        if (c.get("smtp_user") or "").strip():
            valido, errores = validar_config_email_para_guardar(c)
            if not valido:
                raise HTTPException(
                    status_code=400,
                    detail="Cuenta %d: %s" % (i + 1, "; ".join(errores)),
                )

    cuentas_para_bd = []
    for c in cuentas_dict:
        cuentas_para_bd.append(prepare_for_db_storage(dict(c)))

    payload_data = {
        "version": 2,
        "cuentas": cuentas_para_bd,
        "asignacion": asignacion,
        "modo_pruebas": payload.modo_pruebas or "true",
        "email_pruebas": payload.email_pruebas or "",
        "email_activo": payload.email_activo or "true",
        "email_activo_notificaciones": payload.email_activo_notificaciones or "true",
        "email_activo_estado_cuenta": payload.email_activo_estado_cuenta or "true",
        "email_activo_cobros": payload.email_activo_cobros or "true",
        "tickets_notify_emails": payload.tickets_notify_emails or "",
    }
    update_from_api({
        "version": 2,
        "cuentas": cuentas_dict,
        "asignacion": asignacion,
        **{k: v for k, v in payload_data.items() if k not in ("cuentas", "version")},
    })
    try:
        row = db.get(Configuracion, CLAVE_EMAIL_CONFIG)
        payload_str = json.dumps(payload_data)
        if row:
            row.valor = payload_str
        else:
            db.add(Configuracion(clave=CLAVE_EMAIL_CONFIG, valor=payload_str))
        db.commit()
    except Exception as e:
        logger.exception("Error guardando cuentas email: %s", e)
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al guardar en BD")
    return {"message": "Configuracion de 4 cuentas guardada", "version": 2}
