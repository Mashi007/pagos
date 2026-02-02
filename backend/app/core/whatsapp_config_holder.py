"""
Holder de configuración de WhatsApp en tiempo de ejecución.
Usado por Comunicaciones (CRM): webhook y envío/recepción de mensajes.
La API configuracion/whatsapp actualiza la BD; para que Comunicaciones usen la config guardada,
sync_from_db() carga desde la tabla configuracion (clave whatsapp_config) antes de cada uso.
Alineado con email_config_holder para integración Config → CRM.
"""
import json
from typing import Any, Optional

from app.core.config import settings

CLAVE_WHATSAPP_CONFIG = "whatsapp_config"

_current: dict[str, Any] = {}


def _default_config() -> dict[str, Any]:
    """Valores por defecto desde settings (.env)."""
    return {
        "api_url": getattr(settings, "WHATSAPP_GRAPH_URL", None) or "https://graph.facebook.com/v18.0",
        "access_token": getattr(settings, "WHATSAPP_ACCESS_TOKEN", None) or "",
        "phone_number_id": getattr(settings, "WHATSAPP_PHONE_NUMBER_ID", None) or "",
        "business_account_id": getattr(settings, "WHATSAPP_BUSINESS_ACCOUNT_ID", None) or "",
        "webhook_verify_token": getattr(settings, "WHATSAPP_VERIFY_TOKEN", None) or "",
        "app_secret": getattr(settings, "WHATSAPP_APP_SECRET", None) or "",
    }


def sync_from_db() -> None:
    """Carga la configuración de WhatsApp desde la tabla configuracion y actualiza el holder.
    Así Comunicaciones/CRM usan la config guardada en Configuración > WhatsApp."""
    try:
        from app.core.database import SessionLocal
        from app.models.configuracion import Configuracion
        db = SessionLocal()
        try:
            row = db.get(Configuracion, CLAVE_WHATSAPP_CONFIG)
            if row and row.valor:
                data = json.loads(row.valor)
                if isinstance(data, dict):
                    _current.clear()
                    _current.update(_default_config())
                    for k, v in data.items():
                        if k in _current and v is not None:
                            _current[k] = v
        finally:
            db.close()
    except Exception:
        pass


def get_whatsapp_config() -> dict[str, Any]:
    """Devuelve la config WhatsApp actual (holder sincronizado con BD o settings).
    Incluye api_url, access_token, phone_number_id, webhook_verify_token, app_secret."""
    if not _current:
        sync_from_db()
    if _current:
        return {
            "api_url": _current.get("api_url") or _default_config()["api_url"],
            "access_token": _current.get("access_token") or getattr(settings, "WHATSAPP_ACCESS_TOKEN", None) or "",
            "phone_number_id": _current.get("phone_number_id") or getattr(settings, "WHATSAPP_PHONE_NUMBER_ID", None) or "",
            "business_account_id": _current.get("business_account_id") or getattr(settings, "WHATSAPP_BUSINESS_ACCOUNT_ID", None) or "",
            "webhook_verify_token": _current.get("webhook_verify_token") or getattr(settings, "WHATSAPP_VERIFY_TOKEN", None) or "",
            "app_secret": _current.get("app_secret") or getattr(settings, "WHATSAPP_APP_SECRET", None) or "",
        }
    return _default_config()


def get_webhook_verify_token() -> str:
    """Token para verificación del webhook de Meta (desde BD o .env)."""
    cfg = get_whatsapp_config()
    return (cfg.get("webhook_verify_token") or "").strip()


def update_from_api(data: dict[str, Any]) -> None:
    """Actualiza el holder desde la API de configuración (PUT /configuracion/whatsapp/configuracion)."""
    for k in ("api_url", "access_token", "phone_number_id", "business_account_id", "webhook_verify_token", "app_secret"):
        if k in data and data[k] is not None and (data[k] != "***"):
            _current[k] = data[k]
