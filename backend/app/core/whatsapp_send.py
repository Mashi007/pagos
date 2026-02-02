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


def send_whatsapp_text(to_phone: str, body: str) -> tuple[bool, str | None]:
    """
    Envía un mensaje de texto por WhatsApp (Meta Cloud API).
    Usa config desde BD (Configuración > WhatsApp). to_phone: número con o sin +.
    Devuelve (True, None) si se envió, (False, mensaje_error) si no hay config o falló.
    mensaje_error puede ser el detalle de Meta (ej. plantilla requerida).
    """
    phone = _normalize_phone(to_phone)
    if not phone or len(phone) < 10:
        logger.debug("Número WhatsApp inválido o vacío: %s", to_phone)
        return False, "Número inválido o vacío"
    whatsapp_sync_from_db()
    cfg = get_whatsapp_config()
    token = (cfg.get("access_token") or "").strip()
    phone_number_id = (cfg.get("phone_number_id") or "").strip()
    api_url = (cfg.get("api_url") or "https://graph.facebook.com/v18.0").rstrip("/")
    if not token or not phone_number_id:
        logger.warning("WhatsApp no configurado (token o phone_number_id). Configura en Configuración > WhatsApp.")
        return False, "Falta configurar Access Token o Phone Number ID"
    body = (body or "").strip()[:4096]
    if not body:
        return False, "Mensaje vacío"
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
            return True, None
        # Extraer mensaje de Meta para plantilla requerida u otros errores
        error_detail: str | None = None
        try:
            err = r.json()
            msg = (err.get("error") or {}).get("message", "")
            if msg:
                error_detail = msg
                if "template" in msg.lower() or "plantilla" in msg.lower() or "reusable" in msg.lower():
                    error_detail = (
                        "Meta exige una plantilla aprobada para iniciar conversación con este número. "
                        "Crea y aprueba una plantilla en Meta Business Manager (WhatsApp > Plantillas de mensaje) "
                        "o envía primero desde ese número a tu negocio para abrir la ventana de 24 h."
                    )
        except Exception:
            error_detail = r.text[:200] if r.text else f"HTTP {r.status_code}"
        logger.warning("WhatsApp API error %s: %s", r.status_code, error_detail or r.text[:200])
        return False, error_detail or "Error al enviar"
    except Exception as e:
        logger.exception("Error enviando WhatsApp: %s", e)
        return False, str(e)[:200]
