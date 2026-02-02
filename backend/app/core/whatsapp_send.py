"""
Envío de mensajes WhatsApp para Notificaciones (CRM).
Usa configuración desde BD (whatsapp_config_holder) para integrar Configuración > WhatsApp con Notificaciones.
"""
import logging
import re

from app.core.whatsapp_config_holder import get_whatsapp_config, sync_from_db as whatsapp_sync_from_db

logger = logging.getLogger(__name__)


def _normalize_phone(phone: str) -> str:
    """Deja solo dígitos; asegura código de país si parece local (ej. 10 dígitos)."""
    digits = re.sub(r"\D", "", (phone or "").strip())
    if not digits:
        return ""
    # Si tiene 10 dígitos (ej. Venezuela) se asume sin código país; Meta necesita número completo.
    # No añadimos código por defecto; el caller puede pasarlo con +58...
    return digits


def send_whatsapp_text(to_phone: str, body: str) -> bool:
    """
    Envía un mensaje de texto por WhatsApp (Meta Cloud API).
    Usa config desde BD (Configuración > WhatsApp). to_phone: número con o sin +.
    Devuelve True si se envió, False si no hay config o falló.
    """
    phone = _normalize_phone(to_phone)
    if not phone or len(phone) < 10:
        logger.debug("Número WhatsApp inválido o vacío: %s", to_phone)
        return False
    whatsapp_sync_from_db()
    cfg = get_whatsapp_config()
    token = (cfg.get("access_token") or "").strip()
    phone_number_id = (cfg.get("phone_number_id") or "").strip()
    api_url = (cfg.get("api_url") or "https://graph.facebook.com/v18.0").rstrip("/")
    if not token or not phone_number_id:
        logger.warning("WhatsApp no configurado (token o phone_number_id). Configura en Configuración > WhatsApp.")
        return False
    body = (body or "").strip()[:4096]
    if not body:
        return False
    try:
        import httpx
        url = f"{api_url}/{phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone,
            "type": "text",
            "text": {"body": body},
        }
        with httpx.Client(timeout=30.0) as client:
            r = client.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
        if r.is_success:
            logger.info("WhatsApp enviado a %s", phone[:6] + "***")
            return True
        logger.warning("WhatsApp API error %s: %s", r.status_code, r.text[:200])
        return False
    except Exception as e:
        logger.exception("Error enviando WhatsApp: %s", e)
        return False
