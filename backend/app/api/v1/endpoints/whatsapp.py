"""
Endpoints para recibir webhooks de WhatsApp (Meta API)
"""
import logging
import secrets
from fastapi import APIRouter, Request, HTTPException, Query, Depends, Header
from typing import Optional
from app.core.alert_webhook import send_webhook_alert
from app.schemas.whatsapp import (
    WhatsAppWebhookPayload,
    WhatsAppWebhookChallenge,
    WhatsAppMessage,
    WhatsAppContact,
    WhatsAppResponse
)
from app.services.whatsapp_service import WhatsAppService
from app.core.config import settings
from app.core.security_whatsapp import verify_webhook_signature
from app.core.whatsapp_config_holder import get_webhook_verify_token, get_whatsapp_config, sync_from_db as whatsapp_sync_from_db
from app.core.database import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
router = APIRouter()
whatsapp_service = WhatsAppService()


@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
    hub_verify_token: str = Query(..., alias="hub.verify_token")
):
    """
    Endpoint para verificación del webhook de Meta
    
    Meta envía un GET request con estos parámetros para verificar el webhook.
    Debes configurar el mismo token en Meta Developers Console.
    
    Returns:
        El hub.challenge si el token es válido
    """
    try:
        whatsapp_sync_from_db()
        # Token de verificación desde BD (Configuración > WhatsApp) o .env
        verify_token = get_webhook_verify_token()
        if not verify_token:
            verify_token = getattr(settings, "WHATSAPP_VERIFY_TOKEN", None)
        if not verify_token:
            logger.error("Token de verificación del webhook no configurado. Configura en Configuración > WhatsApp o WHATSAPP_VERIFY_TOKEN.")
            raise HTTPException(
                status_code=500,
                detail="Webhook verification token no configurado"
            )
        # Verificar el token usando comparación timing-safe
        if hub_mode == "subscribe" and secrets.compare_digest(hub_verify_token, verify_token):
            logger.info("Webhook de WhatsApp verificado exitosamente")
            # Meta espera recibir el challenge como texto plano
            return int(hub_challenge)
        else:
            logger.debug(
                f"Intento de verificación fallido - Mode: {hub_mode}"
            )
            raise HTTPException(status_code=403, detail="Token de verificación inválido")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en verificación del webhook: {str(e)}", exc_info=True)
        # No exponer detalles del error en producción
        error_detail = "Error verificando webhook" if not settings.DEBUG else str(e)
        raise HTTPException(status_code=500, detail=error_detail)


@router.post("/webhook")
async def receive_webhook(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
    db: Session = Depends(get_db),
):
    """
    Endpoint para recibir mensajes de WhatsApp desde Meta
    
    Meta envía los mensajes entrantes a este endpoint como POST requests.
    
    Args:
        request: Request object con el payload
        x_hub_signature_256: Firma del webhook de Meta (opcional pero recomendado)
    
    Returns:
        Respuesta de confirmación
    """
    try:
        # Obtener el cuerpo del request en bytes para verificación de firma
        body_bytes = await request.body()
        
        whatsapp_sync_from_db()
        # Verificar firma del webhook (si está configurado) ANTES de procesar
        cfg_wa = get_whatsapp_config()
        app_secret = (cfg_wa.get("app_secret") or "").strip() or getattr(settings, "WHATSAPP_APP_SECRET", None)
        if app_secret and x_hub_signature_256:
            if not verify_webhook_signature(body_bytes, x_hub_signature_256, app_secret):
                logger.warning("Firma del webhook inválida - posible request malicioso")
                raise HTTPException(
                    status_code=403,
                    detail="Firma del webhook inválida"
                )
            logger.debug("Firma del webhook verificada correctamente")
        elif app_secret and not x_hub_signature_256:
            logger.warning("App Secret configurado pero no se recibió firma del webhook")
        
        # Obtener el payload JSON después de verificar la firma
        import json
        payload = json.loads(body_bytes.decode('utf-8'))
        logger.info(f"Webhook recibido de WhatsApp: {payload.get('object', 'unknown')}")
        
        # Validar que sea un webhook de WhatsApp Business Account
        if payload.get("object") != "whatsapp_business_account":
            logger.warning(f"Webhook recibido de objeto desconocido: {payload.get('object')}")
            return WhatsAppResponse(
                success=False,
                message="Tipo de webhook no soportado"
            )
        
        # Procesar las entradas del webhook
        entries = payload.get("entry", [])
        processed_messages = []
        
        for entry in entries:
            changes = entry.get("changes", [])
            
            for change in changes:
                value = change.get("value", {})
                
                # Procesar mensajes entrantes
                if value.get("messages"):
                    contacts = {c["wa_id"]: c for c in value.get("contacts", [])}
                    
                    for message_data in value["messages"]:
                        try:
                            # Crear objetos Pydantic
                            message = WhatsAppMessage(**message_data)
                            contact = None
                            
                            if message.from_ in contacts:
                                contact = WhatsAppContact(**contacts[message.from_])
                            
                            # Procesar el mensaje (db para guardar imágenes en pagos_whatsapp)
                            result = await whatsapp_service.process_incoming_message(
                                message=message,
                                contact=contact,
                                db=db,
                            )
                            
                            if result.get("success"):
                                processed_messages.append(result.get("message_id"))
                                logger.info(
                                    f"Mensaje procesado exitosamente - "
                                    f"ID: {result.get('message_id')}"
                                )
                            else:
                                err_msg = result.get("error") or "Error desconocido"
                                logger.error(
                                    f"Error procesando mensaje - "
                                    f"ID: {result.get('message_id')}, "
                                    f"Error: {err_msg}"
                                )
                                send_webhook_alert(
                                    "Error procesando mensaje WhatsApp",
                                    context="whatsapp_webhook",
                                    detail=f"message_id={result.get('message_id')} error={err_msg}",
                                )
                                
                        except Exception as e:
                            logger.error(
                                f"Error procesando mensaje individual: {str(e)}",
                                exc_info=True
                            )
                            send_webhook_alert(
                                "Excepción en webhook WhatsApp",
                                context="whatsapp_webhook",
                                detail=str(e),
                            )
                
                # Procesar estados de mensajes (opcional)
                if value.get("statuses"):
                    for status in value["statuses"]:
                        logger.info(
                            f"Estado de mensaje - ID: {status.get('id')}, "
                            f"Status: {status.get('status')}"
                        )
        
        # Retornar respuesta exitosa
        return WhatsAppResponse(
            success=True,
            message=f"Webhook procesado. {len(processed_messages)} mensaje(s) procesado(s)",
            message_id=processed_messages[0] if processed_messages else None
        )
        
    except Exception as e:
        logger.error(f"Error procesando webhook de WhatsApp: {str(e)}", exc_info=True)
        send_webhook_alert(
            "Webhook WhatsApp: excepción no controlada (5xx)",
            context="whatsapp_webhook",
            detail=str(e),
        )
        # No exponer detalles del error en producción
        error_message = "Error procesando webhook" if not settings.DEBUG else str(e)
        return WhatsAppResponse(
            success=False,
            message=error_message
        )
