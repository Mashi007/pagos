"""
Endpoints para recibir webhooks de WhatsApp (Meta API)
"""
import logging
from fastapi import APIRouter, Request, HTTPException, Query, Depends
from typing import Optional
from app.schemas.whatsapp import (
    WhatsAppWebhookPayload,
    WhatsAppWebhookChallenge,
    WhatsAppMessage,
    WhatsAppContact,
    WhatsAppResponse
)
from app.services.whatsapp_service import WhatsAppService
from app.core.config import settings

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
        # Obtener el token de verificación desde configuración
        verify_token = getattr(settings, "WHATSAPP_VERIFY_TOKEN", None)
        
        if not verify_token:
            logger.error("WHATSAPP_VERIFY_TOKEN no configurado en settings")
            raise HTTPException(
                status_code=500,
                detail="Webhook verification token no configurado"
            )
        
        # Verificar el token
        if hub_mode == "subscribe" and hub_verify_token == verify_token:
            logger.info("Webhook de WhatsApp verificado exitosamente")
            # Meta espera recibir el challenge como texto plano
            return int(hub_challenge)
        else:
            logger.warning(
                f"Intento de verificación fallido - Mode: {hub_mode}, "
                f"Token recibido: {hub_verify_token[:5]}..."
            )
            raise HTTPException(status_code=403, detail="Token de verificación inválido")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en verificación del webhook: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error verificando webhook")


@router.post("/webhook")
async def receive_webhook(request: Request):
    """
    Endpoint para recibir mensajes de WhatsApp desde Meta
    
    Meta envía los mensajes entrantes a este endpoint como POST requests.
    
    Returns:
        Respuesta de confirmación
    """
    try:
        # Obtener el payload JSON
        payload = await request.json()
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
                            
                            # Procesar el mensaje
                            result = await whatsapp_service.process_incoming_message(
                                message=message,
                                contact=contact
                            )
                            
                            if result.get("success"):
                                processed_messages.append(result.get("message_id"))
                                logger.info(
                                    f"Mensaje procesado exitosamente - "
                                    f"ID: {result.get('message_id')}"
                                )
                            else:
                                logger.error(
                                    f"Error procesando mensaje - "
                                    f"ID: {result.get('message_id')}, "
                                    f"Error: {result.get('error')}"
                                )
                                
                        except Exception as e:
                            logger.error(
                                f"Error procesando mensaje individual: {str(e)}",
                                exc_info=True
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
        return WhatsAppResponse(
            success=False,
            message=f"Error procesando webhook: {str(e)}"
        )
