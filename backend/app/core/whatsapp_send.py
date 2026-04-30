"""
Envío de mensajes WhatsApp para Notificaciones (CRM).
Usa configuración desde BD (whatsapp_config_holder) para integrar Configuración > WhatsApp con Notificaciones.
"""
import logging
import re

from app.core.config import settings
from app.core.whatsapp_config_holder import get_whatsapp_config, sync_from_db as whatsapp_sync_from_db

logger = logging.getLogger(__name__)

# Meta (#133010) "Account not registered": número WABA no registrado para Cloud API; evita WARNING por cada envío.
_whatsapp_133010_logged = False
_whatsapp_send_disabled_logged = False


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
    if not settings.WHATSAPP_SEND_ENABLED:
        global _whatsapp_send_disabled_logged
        if not _whatsapp_send_disabled_logged:
            _whatsapp_send_disabled_logged = True
            logger.info(
                "WhatsApp/Meta desactivado (WHATSAPP_SEND_ENABLED=false): sin llamadas a Graph API. "
                "Para reactivar: WHATSAPP_SEND_ENABLED=true y reiniciar el proceso."
            )
        return False, "WhatsApp desactivado en el servidor (WHATSAPP_SEND_ENABLED=false)"
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
        meta_code: int | None = None
        fbtrace: str | None = None
        try:
            err = r.json()
            err_o = err.get("error") or {}
            msg = (err_o.get("message") or "") if isinstance(err_o, dict) else ""
            if isinstance(err_o, dict):
                c = err_o.get("code")
                if isinstance(c, int):
                    meta_code = c
                elif isinstance(c, str) and c.isdigit():
                    meta_code = int(c)
                fbtrace = err_o.get("fbtrace_id") if isinstance(err_o.get("fbtrace_id"), str) else None
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
        msg_l = (error_detail or "").lower()
        is_133010 = meta_code == 133010 or "account not registered" in msg_l
        if is_133010:
            global _whatsapp_133010_logged
            if not _whatsapp_133010_logged:
                _whatsapp_133010_logged = True
                logger.warning(
                    "WhatsApp API error %s (#133010 Account not registered): el número de la app (phone_number_id) "
                    "no está registrado en la plataforma WhatsApp Business / Cloud API. "
                    "Revise Meta Business Suite: WhatsApp > API de configuración — registrar el número, "
                    "o confirme que el Phone number ID y el token corresponden al mismo activo. "
                    "Doc: developers.facebook.com/docs/whatsapp/cloud-api/reference/registration. "
                    "fbtrace_id=%s",
                    r.status_code,
                    fbtrace or "—",
                )
            else:
                logger.debug(
                    "WhatsApp API error %s (#133010) omitido (ya se registró aviso operativo).",
                    r.status_code,
                )
        else:
            logger.warning("WhatsApp API error %s: %s", r.status_code, error_detail or r.text[:200])
        return False, error_detail or "Error al enviar"
    except Exception as e:
        logger.exception("Error enviando WhatsApp: %s", e)
        return False, str(e)[:200]
