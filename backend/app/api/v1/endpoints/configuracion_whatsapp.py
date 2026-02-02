"""
Endpoints de configuración WhatsApp para Comunicaciones.
GET/PUT /configuracion/whatsapp/configuracion.
Políticas: no exponer access_token en GET (se devuelve ***), no sobrescribir token
cuando el frontend envía valor enmascarado (*** o vacío). Persiste en BD (tabla configuracion).
"""
import json
import logging
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.configuracion import Configuracion

logger = logging.getLogger(__name__)
router = APIRouter()

CLAVE_WHATSAPP_CONFIG = "whatsapp_config"

# Stub en memoria; se sincroniza con BD
_whatsapp_stub: dict[str, Any] = {}


def _default_config() -> dict[str, Any]:
    """Valores por defecto desde settings."""
    return {
        "api_url": getattr(settings, "WHATSAPP_GRAPH_URL", None) or "https://graph.facebook.com/v18.0",
        "access_token": getattr(settings, "WHATSAPP_ACCESS_TOKEN", None) or "",
        "phone_number_id": getattr(settings, "WHATSAPP_PHONE_NUMBER_ID", None) or "",
        "business_account_id": getattr(settings, "WHATSAPP_BUSINESS_ACCOUNT_ID", None) or "",
        "webhook_verify_token": getattr(settings, "WHATSAPP_VERIFY_TOKEN", None) or "",
        "modo_pruebas": "true",
        "telefono_pruebas": "",
    }


def _load_whatsapp_from_db(db: Session) -> None:
    """Carga configuración WhatsApp desde la tabla configuracion."""
    try:
        row = db.get(Configuracion, CLAVE_WHATSAPP_CONFIG)
        if row and row.valor:
            data = json.loads(row.valor)
            if isinstance(data, dict):
                _whatsapp_stub.clear()
                _whatsapp_stub.update(_default_config())
                for k, v in data.items():
                    if k in _whatsapp_stub and v is not None:
                        _whatsapp_stub[k] = v
    except Exception:
        pass


def _save_whatsapp_to_db(db: Session) -> None:
    """Persiste configuración WhatsApp en la tabla configuracion."""
    try:
        payload = json.dumps(_whatsapp_stub)
        row = db.get(Configuracion, CLAVE_WHATSAPP_CONFIG)
        if row:
            row.valor = payload
        else:
            db.add(Configuracion(clave=CLAVE_WHATSAPP_CONFIG, valor=payload))
        db.commit()
    except Exception:
        db.rollback()
        raise


def _is_token_masked(v: Any) -> bool:
    """No sobrescribir el token real con el valor enmascarado que envía el frontend."""
    if v is None:
        return True
    if not isinstance(v, str):
        return True
    s = (v or "").strip()
    return s == "" or s == "***"


@router.get("/configuracion")
def get_whatsapp_configuracion(db: Session = Depends(get_db)):
    """Configuración WhatsApp. NUNCA expone access_token ni webhook_verify_token en texto plano (se devuelve ***)."""
    _load_whatsapp_from_db(db)
    if not _whatsapp_stub:
        _whatsapp_stub.update(_default_config())
    out = _whatsapp_stub.copy()
    if out.get("access_token"):
        out["access_token"] = "***"
    if out.get("webhook_verify_token"):
        out["webhook_verify_token"] = "***"
    return out


class WhatsAppConfigUpdate(BaseModel):
    api_url: Optional[str] = None
    access_token: Optional[str] = None
    phone_number_id: Optional[str] = None
    business_account_id: Optional[str] = None
    webhook_verify_token: Optional[str] = None
    modo_pruebas: Optional[str] = None
    telefono_pruebas: Optional[str] = None


@router.put("/configuracion")
def put_whatsapp_configuracion(payload: WhatsAppConfigUpdate = Body(...), db: Session = Depends(get_db)):
    """Actualizar configuración WhatsApp. No sobrescribe access_token ni webhook_verify_token si el frontend envía *** o vacío. Persiste en BD."""
    _load_whatsapp_from_db(db)
    if not _whatsapp_stub:
        _whatsapp_stub.update(_default_config())
    data = payload.model_dump(exclude_none=True)
    for k, v in data.items():
        if k not in _whatsapp_stub:
            continue
        if k in ("access_token", "webhook_verify_token") and _is_token_masked(v):
            continue
        _whatsapp_stub[k] = v
    _save_whatsapp_to_db(db)
    logger.info("Configuración WhatsApp actualizada y persistida en BD (campos: %s)", list(data.keys()))
    out = _whatsapp_stub.copy()
    if out.get("access_token"):
        out["access_token"] = "***"
    if out.get("webhook_verify_token"):
        out["webhook_verify_token"] = "***"
    return {"message": "Configuración WhatsApp actualizada", "configuracion": out}
