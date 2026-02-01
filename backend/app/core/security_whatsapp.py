"""
Utilidades de seguridad para webhooks de WhatsApp
"""
import hmac
import hashlib
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def verify_webhook_signature(
    payload_body: bytes,
    signature_header: Optional[str],
    app_secret: Optional[str]
) -> bool:
    """
    Verifica la firma del webhook de Meta usando X-Hub-Signature-256
    
    Args:
        payload_body: Cuerpo del request en bytes
        signature_header: Valor del header X-Hub-Signature-256
        app_secret: App Secret de Meta (WHATSAPP_APP_SECRET)
        
    Returns:
        True si la firma es válida
    """
    if not app_secret or not signature_header:
        logger.warning("App Secret o Signature header no proporcionados - saltando verificación")
        return False
    
    try:
        # Meta envía la firma como "sha256=<hash>"
        if signature_header.startswith("sha256="):
            signature = signature_header[7:]  # Remover "sha256="
        else:
            signature = signature_header
        
        # Calcular el hash esperado
        expected_signature = hmac.new(
            app_secret.encode('utf-8'),
            payload_body,
            hashlib.sha256
        ).hexdigest()
        
        # Comparar de forma segura (timing-safe)
        return hmac.compare_digest(signature, expected_signature)
        
    except Exception as e:
        logger.error(f"Error verificando firma del webhook: {str(e)}", exc_info=True)
        return False
