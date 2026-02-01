"""
Endpoints de configuración WhatsApp para Comunicaciones.
GET/PUT /configuracion/whatsapp/configuracion (usa settings o stub en memoria).
Comunicaciones (frontend) usa esta config para enviar/recibir por WhatsApp.
"""
from typing import Any, Optional
from fastapi import APIRouter, Body
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()

# Stub en memoria para PUT (prioridad sobre env si el frontend guarda)
_whatsapp_stub: dict[str, Any] = {}


def _get_config() -> dict[str, Any]:
    """Config WhatsApp: stub si existe, sino settings."""
    if _whatsapp_stub:
        return {**_whatsapp_stub}
    return {
        "api_url": getattr(settings, "WHATSAPP_GRAPH_URL", None) or "https://graph.facebook.com/v18.0",
        "access_token": getattr(settings, "WHATSAPP_ACCESS_TOKEN", None) or "",
        "phone_number_id": getattr(settings, "WHATSAPP_PHONE_NUMBER_ID", None) or "",
        "business_account_id": getattr(settings, "WHATSAPP_BUSINESS_ACCOUNT_ID", None) or "",
        "webhook_verify_token": getattr(settings, "WHATSAPP_VERIFY_TOKEN", None) or "",
        "modo_pruebas": "true",
        "telefono_pruebas": "",
    }


class WhatsAppConfigUpdate(BaseModel):
    api_url: Optional[str] = None
    access_token: Optional[str] = None
    phone_number_id: Optional[str] = None
    business_account_id: Optional[str] = None
    webhook_verify_token: Optional[str] = None
    modo_pruebas: Optional[str] = None
    telefono_pruebas: Optional[str] = None


@router.get("/configuracion")
def get_whatsapp_configuracion():
    """Configuración WhatsApp para Comunicaciones (y Configuración?tab=whatsapp)."""
    return _get_config()


@router.put("/configuracion")
def put_whatsapp_configuracion(payload: WhatsAppConfigUpdate = Body(...)):
    """Actualizar configuración WhatsApp (stub en memoria)."""
    data = payload.model_dump(exclude_none=True)
    _whatsapp_stub.update(data)
    return {"message": "Configuración WhatsApp actualizada", "configuracion": _get_config()}
