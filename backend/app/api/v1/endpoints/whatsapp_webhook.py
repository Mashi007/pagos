"""
Endpoints de Webhook para WhatsApp Business API
Compatibles con Meta WhatsApp Business API y n8n
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.notificacion import Notificacion
from app.services.whatsapp_service import WhatsAppService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/whatsapp/webhook")
async def verify_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    db: Session = Depends(get_db),
):
    """
    Endpoint de verificación de webhook para Meta WhatsApp Business API
    
    Meta envía un GET request con:
    - hub.mode: "subscribe"
    - hub.verify_token: El token que configuraste
    - hub.challenge: Un string aleatorio que debes retornar
    
    Este endpoint también funciona para n8n cuando se configura como webhook público.
    
    Returns:
        PlainTextResponse con hub.challenge si el token es válido
    """
    try:
        # Obtener configuración de WhatsApp
        whatsapp_service = WhatsAppService(db=db)
        expected_token = whatsapp_service.webhook_verify_token

        # Verificar que el modo sea "subscribe"
        if hub_mode != "subscribe":
            logger.warning(f"⚠️ Webhook verification: modo inválido '{hub_mode}'")
            raise HTTPException(status_code=403, detail="Modo inválido")

        # Verificar el token
        if not hub_verify_token or hub_verify_token != expected_token:
            logger.warning(
                f"⚠️ Webhook verification: token inválido. Esperado: {expected_token[:10] if expected_token else 'None'}..., "
                f"Recibido: {hub_verify_token[:10] if hub_verify_token else 'None'}..."
            )
            raise HTTPException(status_code=403, detail="Token de verificación inválido")

        # Si llegamos aquí, el token es válido
        logger.info(f"✅ Webhook verificado exitosamente. Challenge: {hub_challenge}")
        
        # Retornar el challenge como texto plano (requerido por Meta)
        return PlainTextResponse(content=hub_challenge or "")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error verificando webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post("/whatsapp/webhook")
async def receive_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
):
    """
    Endpoint para recibir eventos de WhatsApp Business API
    
    Meta envía eventos cuando:
    - Se recibe un mensaje
    - Un mensaje es entregado
    - Un mensaje es leído
    - Ocurre un error
    
    Este endpoint también puede recibir eventos desde n8n si se configura como intermediario.
    
    Headers esperados:
        X-Hub-Signature-256: Firma HMAC SHA256 del payload (opcional, para validación)
    
    Body:
        JSON con estructura de eventos de Meta:
        {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "...",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {...},
                                "statuses": [...],  # Para actualizaciones de estado
                                "messages": [...]   # Para mensajes recibidos
                            }
                        }
                    ]
                }
            ]
        }
    """
    try:
        # Obtener payload
        payload = await request.json()
        
        logger.info(f"📨 Webhook recibido: {payload.get('object', 'unknown')}")
        
        # Verificar que sea un evento de WhatsApp
        if payload.get("object") != "whatsapp_business_account":
            logger.warning(f"⚠️ Webhook recibido con object inválido: {payload.get('object')}")
            return {"status": "ignored", "reason": "Not a WhatsApp Business Account event"}

        # Procesar cada entrada
        entries = payload.get("entry", [])
        eventos_procesados = 0
        errores = []

        for entry in entries:
            changes = entry.get("changes", [])
            
            for change in changes:
                value = change.get("value", {})
                
                # Procesar actualizaciones de estado (mensajes enviados, entregados, leídos)
                if "statuses" in value:
                    eventos_procesados += await _procesar_estados(value["statuses"], db)
                
                # Procesar mensajes recibidos
                if "messages" in value:
                    eventos_procesados += await _procesar_mensajes_recibidos(value["messages"], db)
                
                # Procesar errores
                if "errors" in value:
                    errores.extend(value["errors"])
                    logger.error(f"❌ Errores en webhook: {value['errors']}")

        logger.info(f"✅ Webhook procesado: {eventos_procesados} eventos procesados")
        
        # Retornar 200 OK para confirmar recepción
        return {
            "status": "success",
            "eventos_procesados": eventos_procesados,
            "errores": len(errores),
        }

    except Exception as e:
        logger.error(f"❌ Error procesando webhook: {e}", exc_info=True)
        # Retornar 200 para evitar que Meta reintente inmediatamente
        # Pero registrar el error para debugging
        return {"status": "error", "message": str(e)}


async def _procesar_estados(statuses: list, db: Session) -> int:
    """
    Procesar actualizaciones de estado de mensajes
    
    Actualiza el estado de las notificaciones según los webhooks de Meta:
    - sent: Mensaje enviado
    - delivered: Mensaje entregado
    - read: Mensaje leído
    - failed: Mensaje fallido
    """
    eventos_procesados = 0
    
    try:
        for status in statuses:
            message_id = status.get("id")
            status_value = status.get("status")  # sent, delivered, read, failed
            recipient_id = status.get("recipient_id")
            timestamp = status.get("timestamp")
            
            if not message_id:
                continue
            
            # Buscar notificación por message_id
            # El message_id se guarda en respuesta_servicio cuando se envía el mensaje
            notificacion = None
            if message_id:
                # Buscar notificaciones WhatsApp recientes y verificar si el message_id está en respuesta_servicio
                notificaciones_whatsapp = (
                    db.query(Notificacion)
                    .filter(
                        Notificacion.canal == "WHATSAPP",
                        Notificacion.respuesta_servicio.isnot(None),
                    )
                    .order_by(Notificacion.id.desc())
                    .limit(100)  # Buscar en las últimas 100 notificaciones
                    .all()
                )
                
                # Buscar el message_id en respuesta_servicio
                for notif in notificaciones_whatsapp:
                    if notif.respuesta_servicio and message_id in notif.respuesta_servicio:
                        notificacion = notif
                        break
            
            if notificacion:
                # Actualizar estado según el status de Meta
                if status_value == "sent":
                    # Ya estaba como ENVIADA, solo actualizar timestamp si es necesario
                    logger.debug(f"📤 Mensaje {message_id} enviado")
                elif status_value == "delivered":
                    # Opcional: agregar campo "entregado_en" si existe
                    logger.info(f"✅ Mensaje {message_id} entregado a {recipient_id}")
                elif status_value == "read":
                    # Opcional: agregar campo "leido_en" si existe
                    logger.info(f"👁️ Mensaje {message_id} leído por {recipient_id}")
                elif status_value == "failed":
                    notificacion.estado = "FALLIDA"
                    error_info = status.get("errors", [])
                    if error_info:
                        notificacion.error_mensaje = str(error_info[0].get("message", "Error desconocido"))
                    logger.error(f"❌ Mensaje {message_id} falló: {error_info}")
                
                db.commit()
                eventos_procesados += 1
            else:
                logger.debug(f"⚠️ No se encontró notificación para message_id: {message_id}")
    
    except Exception as e:
        logger.error(f"❌ Error procesando estados: {e}", exc_info=True)
        db.rollback()
    
    return eventos_procesados


async def _procesar_mensajes_recibidos(messages: list, db: Session) -> int:
    """
    Procesar mensajes recibidos de clientes
    
    Esto permite recibir mensajes de clientes y responder automáticamente.
    Por ahora solo registramos los mensajes recibidos.
    """
    eventos_procesados = 0
    
    try:
        for message in messages:
            from_number = message.get("from")
            message_id = message.get("id")
            message_type = message.get("type")
            timestamp = message.get("timestamp")
            
            # Extraer contenido según el tipo
            if message_type == "text":
                body = message.get("text", {}).get("body", "")
            elif message_type == "image":
                body = "[Imagen recibida]"
            elif message_type == "document":
                body = "[Documento recibido]"
            else:
                body = f"[Mensaje tipo: {message_type}]"
            
            logger.info(
                f"📨 Mensaje recibido de {from_number}: {body[:50]}... "
                f"(ID: {message_id}, Tipo: {message_type})"
            )
            
            # Aquí podrías:
            # 1. Guardar el mensaje en una tabla de mensajes recibidos
            # 2. Procesar comandos automáticos
            # 3. Enviar respuestas automáticas
            # 4. Actualizar última interacción del cliente (para ventana de 24h)
            
            eventos_procesados += 1
    
    except Exception as e:
        logger.error(f"❌ Error procesando mensajes recibidos: {e}", exc_info=True)
    
    return eventos_procesados


@router.get("/whatsapp/webhook/info")
async def webhook_info(db: Session = Depends(get_db)):
    """
    Obtener información del webhook para configuración en Meta y n8n
    
    Retorna:
        - URL del webhook
        - Token de verificación
        - Instrucciones de configuración
    """
    try:
        whatsapp_service = WhatsAppService(db=db)
        
        # Construir URL del webhook (asumiendo que se accede desde la misma base URL)
        from app.core.config import settings
        
        # Intentar obtener la URL base desde settings o usar una por defecto
        base_url = getattr(settings, "BASE_URL", "https://tu-dominio.com")
        webhook_url = f"{base_url}/api/v1/whatsapp/webhook"
        
        return {
            "webhook_url": webhook_url,
            "verify_token_configured": bool(whatsapp_service.webhook_verify_token),
            "verify_token_preview": (
                whatsapp_service.webhook_verify_token[:10] + "..." if whatsapp_service.webhook_verify_token else "No configurado"
            ),
            "instrucciones": {
                "meta": {
                    "paso_1": "Ve a Meta Developers: https://developers.facebook.com/apps",
                    "paso_2": "Selecciona tu app y ve a WhatsApp > Configuration",
                    "paso_3": f"Configura Webhook URL: {webhook_url}",
                    "paso_4": f"Configura Verify Token: (el token configurado en la aplicación)",
                    "paso_5": "Suscríbete a los eventos: messages, messaging_postbacks",
                },
                "n8n": {
                    "opcion_1": "Usar n8n como intermediario: Configura webhook público en n8n que reciba de Meta y reenvíe a este endpoint",
                    "opcion_2": "Usar este endpoint directamente: Configura Meta para enviar directamente a este endpoint",
                    "paso_1": "Crea un workflow en n8n con trigger 'Webhook'",
                    "paso_2": "Configura el webhook como público y copia la URL",
                    "paso_3": "En Meta, configura esa URL de n8n como webhook",
                    "paso_4": "En n8n, agrega un nodo HTTP Request que envíe los eventos a este endpoint",
                },
            },
        }
    
    except Exception as e:
        logger.error(f"❌ Error obteniendo info de webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

