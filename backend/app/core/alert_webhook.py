"""
Aviso cuando el webhook de WhatsApp falla (5xx o error de procesamiento).
Envía un POST a ALERT_WEBHOOK_URL (ej. Slack Incoming Webhook) si está configurado.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def send_webhook_alert(
    message: str,
    context: str = "whatsapp_webhook",
    detail: Optional[str] = None,
    url: Optional[str] = None,
) -> bool:
    """
    Envía un aviso a la URL configurada (Slack u otro endpoint que acepte POST JSON).
    Si url no se pasa, se usa settings.ALERT_WEBHOOK_URL.
    Retorna True si se envió correctamente, False en caso contrario.
    """
    try:
        from app.core.config import settings
        alert_url = url or getattr(settings, "ALERT_WEBHOOK_URL", None)
        if not alert_url or not str(alert_url).strip():
            return False
        alert_url = str(alert_url).strip()
        import httpx
        body: dict
        # Slack Incoming Webhook acepta { "text": "..." }
        if "slack.com" in alert_url:
            text = message
            if detail:
                text += f"\nDetalle: {detail}"
            body = {"text": f"[{context}] {text}"}
        else:
            body = {
                "message": message,
                "context": context,
                "detail": detail,
            }
        with httpx.Client(timeout=10.0) as client:
            r = client.post(alert_url, json=body)
            if r.is_success:
                logger.debug("Alerta webhook enviada a %s", alert_url[:50])
                return True
            logger.warning("Alerta webhook falló status=%s url=%s", r.status_code, alert_url[:50])
            return False
    except Exception as e:
        logger.warning("No se pudo enviar alerta webhook: %s", e)
        return False
