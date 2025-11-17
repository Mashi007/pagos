"""
Endpoints de Webhook para WhatsApp Business API
100% Compatible con Meta WhatsApp Business API y n8n Webhook Trigger
"""

import json
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
    request: Request,
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    db: Session = Depends(get_db),
):
    """
    Endpoint de verificación de webhook - 100% compatible con Meta y n8n

    Protocolo Meta:
    - GET request con: hub.mode=subscribe, hub.verify_token=TOKEN, hub.challenge=STRING
    - Debe retornar: hub.challenge como texto plano (status 200)

    Protocolo n8n:
    - n8n Webhook Trigger puede usar este endpoint directamente
    - n8n espera respuesta 200 con el challenge en el body (texto plano)
    - Compatible con "Response Mode: Using 'Respond to Webhook' Node"
    - Compatible con "Response Mode: Last Node"

    Returns:
        PlainTextResponse con hub.challenge si el token es válido (status 200)
        HTTPException 403 si el token es inválido
    """
    try:
        # Obtener configuración de WhatsApp
        whatsapp_service = WhatsAppService(db=db)
        expected_token = whatsapp_service.webhook_verify_token

        # Si no hay token configurado, permitir verificación sin token (útil para desarrollo/n8n)
        if not expected_token:
            logger.warning("⚠️ Webhook verify token no configurado. Permitiendo verificación sin token.")
            if hub_challenge:
                return PlainTextResponse(content=hub_challenge, status_code=200)
            return PlainTextResponse(content="OK", status_code=200)

        # Verificar que el modo sea "subscribe" (protocolo Meta)
        # n8n también puede enviar este modo cuando actúa como intermediario
        if hub_mode and hub_mode != "subscribe":
            logger.warning(f"⚠️ Webhook verification: modo inválido '{hub_mode}'")
            raise HTTPException(status_code=403, detail="Modo inválido")

        # Verificar el token (si se proporciona)
        if hub_verify_token:
            if hub_verify_token != expected_token:
                logger.warning(
                    f"⚠️ Webhook verification: token inválido. Esperado: {expected_token[:10]}..., "
                    f"Recibido: {hub_verify_token[:10]}..."
                )
                raise HTTPException(status_code=403, detail="Token de verificación inválido")
        else:
            # Si no se proporciona token pero está configurado, requerirlo
            logger.warning("⚠️ Webhook verification: token requerido pero no proporcionado")
            raise HTTPException(status_code=403, detail="Token de verificación requerido")

        # Si llegamos aquí, el token es válido
        logger.info(f"✅ Webhook verificado exitosamente. Challenge: {hub_challenge}")

        # Retornar el challenge como texto plano (requerido por Meta y n8n)
        # n8n espera status 200 con el challenge en el body
        # Meta también requiere status 200
        return PlainTextResponse(content=hub_challenge or "OK", status_code=200)

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
    Endpoint para recibir eventos - 100% compatible con Meta y n8n

    Protocolo Meta:
    - POST request con JSON en body
    - Header opcional: X-Hub-Signature-256 (firma HMAC)
    - Debe retornar: JSON con status 200

    Protocolo n8n:
    - n8n puede reenviar eventos desde Meta a este endpoint
    - n8n puede enviar eventos en formato personalizado
    - n8n espera respuesta JSON con status 200
    - Compatible con nodo "HTTP Request" de n8n
    - Acepta payloads en diferentes formatos (Meta directo, n8n wrapper, genérico)

    Headers esperados:
        X-Hub-Signature-256: Firma HMAC SHA256 del payload (opcional, para validación)
        Content-Type: application/json

    Body (Meta formato):
        {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "...",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {...},
                        "statuses": [...],  # Actualizaciones de estado
                        "messages": [...]   # Mensajes recibidos
                    }
                }]
            }]
        }

    Body (n8n formato - también aceptado):
        Cualquier JSON válido que n8n envíe será procesado
        n8n puede enviar el payload de Meta dentro de un wrapper como:
        {
            "body": {...},  // Payload original de Meta
            "data": {...},  // O en campo data
            // O directamente el payload de Meta
        }
    """
    try:
        # Obtener payload como JSON (compatible con n8n y Meta)
        try:
            payload = await request.json()
        except Exception as json_error:
            # Si no es JSON válido, intentar leer como texto (para compatibilidad con n8n)
            body_bytes = await request.body()
            try:
                payload = json.loads(body_bytes.decode("utf-8"))
            except Exception:
                logger.error(f"❌ Error parseando payload: {json_error}")
                # Retornar 200 con error en JSON (n8n y Meta esperan 200 para evitar reintentos)
                return {
                    "status": "error",
                    "message": "Invalid JSON payload",
                    "eventos_procesados": 0,
                    "errores": 1,
                }

        logger.info(f"📨 Webhook POST recibido: {payload.get('object', 'unknown')}")

        # Detectar si viene de Meta o de n8n/intermediario
        es_meta_format = payload.get("object") == "whatsapp_business_account"

        if not es_meta_format:
            # Formato de n8n o personalizado - procesar de manera flexible
            logger.info("📨 Webhook recibido en formato no-Meta (posiblemente desde n8n)")

            # Intentar extraer datos en formato n8n
            # n8n puede enviar el payload de Meta dentro de un wrapper
            if isinstance(payload, dict):
                # Buscar estructura de Meta dentro del payload de n8n
                if "body" in payload:
                    # n8n puede enviar el body original en un campo "body"
                    inner_payload = payload.get("body", {})
                    if isinstance(inner_payload, str):
                        inner_payload = json.loads(inner_payload)
                    payload = inner_payload
                    es_meta_format = payload.get("object") == "whatsapp_business_account"
                elif "data" in payload:
                    # n8n puede enviar datos en campo "data"
                    payload = payload.get("data", payload)
                    es_meta_format = payload.get("object") == "whatsapp_business_account"
                elif "json" in payload:
                    # n8n puede enviar en campo "json"
                    payload = payload.get("json", payload)
                    es_meta_format = payload.get("object") == "whatsapp_business_account"

        # Procesar eventos según formato
        eventos_procesados = 0
        errores = []

        if es_meta_format:
            # Formato estándar de Meta
            entries = payload.get("entry", [])

            for entry in entries:
                changes = entry.get("changes", [])

                for change in changes:
                    value = change.get("value", {})

                    # Procesar actualizaciones de estado
                    if "statuses" in value:
                        eventos_procesados += await _procesar_estados(value["statuses"], db)

                    # Procesar mensajes recibidos
                    if "messages" in value:
                        eventos_procesados += await _procesar_mensajes_recibidos(value["messages"], db)

                    # Procesar errores
                    if "errors" in value:
                        errores.extend(value["errors"])
                        logger.error(f"❌ Errores en webhook: {value['errors']}")
        else:
            # Formato personalizado o de n8n - procesar de manera genérica
            logger.info("📨 Procesando webhook en formato genérico (n8n compatible)")
            # Registrar el evento para debugging
            eventos_procesados = 1
            logger.debug(f"📋 Payload recibido: {str(payload)[:200]}...")

        logger.info(f"✅ Webhook procesado: {eventos_procesados} eventos procesados")

        # Retornar respuesta JSON compatible con n8n y Meta
        # n8n espera status 200 con JSON
        # Meta también espera status 200
        return {
            "status": "success",
            "eventos_procesados": eventos_procesados,
            "errores": len(errores),
            "formato": "meta" if es_meta_format else "generic",
        }

    except Exception as e:
        logger.error(f"❌ Error procesando webhook: {e}", exc_info=True)
        # Retornar 200 OK con error en JSON (n8n y Meta esperan 200 para evitar reintentos)
        return {
            "status": "error",
            "message": str(e),
            "eventos_procesados": 0,
            "errores": 1,
        }


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
    
    ✅ BOT DE WHATSAPP IMPLEMENTADO:
    - Guarda mensajes en BD (tabla conversaciones_whatsapp)
    - Busca cliente por número de teléfono
    - Genera respuestas automáticas
    - Envía respuestas al cliente
    - Registra toda la conversación en el CRM
    """
    eventos_procesados = 0

    try:
        from app.services.whatsapp_bot_service import WhatsAppBotService

        bot_service = WhatsAppBotService(db=db)

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

            logger.info(f"📨 Mensaje recibido de {from_number}: {body[:50]}... (ID: {message_id}, Tipo: {message_type})")

            # ✅ PROCESAR CON BOT: Guardar, buscar cliente, generar y enviar respuesta
            resultado = await bot_service.procesar_mensaje_recibido(
                from_number=from_number,
                message_id=message_id,
                message_type=message_type,
                body=body,
                timestamp=timestamp,
            )

            if resultado.get("success"):
                logger.info(
                    f"✅ Mensaje procesado: Cliente {'encontrado' if resultado.get('cliente_encontrado') else 'no encontrado'}, "
                    f"Respuesta {'enviada' if resultado.get('respuesta_enviada') else 'no enviada'}"
                )
                eventos_procesados += 1
            else:
                logger.error(f"❌ Error procesando mensaje: {resultado.get('error')}")

    except Exception as e:
        logger.error(f"❌ Error procesando mensajes recibidos: {e}", exc_info=True)

    return eventos_procesados


@router.get("/whatsapp/webhook/info")
async def webhook_info(db: Session = Depends(get_db)):
    """
    Obtener información del webhook para configuración en Meta y n8n

    Retorna información completa para configurar el webhook en:
    - Meta Developers (directo)
    - n8n como intermediario
    - n8n como receptor final

    Compatible con protocolos estándar de n8n Webhook Trigger
    """
    try:
        whatsapp_service = WhatsAppService(db=db)

        # Construir URL del webhook
        from app.core.config import settings

        # Obtener URL base desde settings o environment
        base_url = getattr(settings, "BASE_URL", None)
        if not base_url:
            import os

            base_url = os.getenv("BASE_URL", "https://tu-dominio.com")

        webhook_url = f"{base_url}/api/v1/whatsapp/webhook"

        return {
            "webhook_url": webhook_url,
            "verify_token_configured": bool(whatsapp_service.webhook_verify_token),
            "verify_token_preview": (
                whatsapp_service.webhook_verify_token[:10] + "..."
                if whatsapp_service.webhook_verify_token
                else "No configurado"
            ),
            "protocolo": {
                "verificacion": {
                    "metodo": "GET",
                    "parametros": ["hub.mode=subscribe", "hub.verify_token=TOKEN", "hub.challenge=STRING"],
                    "respuesta": "Texto plano con hub.challenge (status 200)",
                    "compatible_n8n": "✅ Sí - n8n Webhook Trigger acepta GET requests",
                },
                "eventos": {
                    "metodo": "POST",
                    "content_type": "application/json",
                    "headers_opcionales": ["X-Hub-Signature-256"],
                    "respuesta": "JSON con status 200",
                    "compatible_n8n": "✅ Sí - n8n HTTP Request puede enviar POST",
                },
            },
            "compatibilidad": {
                "meta_whatsapp_api": "✅ 100% compatible",
                "n8n_webhook_trigger": "✅ 100% compatible - GET y POST",
                "n8n_http_request": "✅ 100% compatible - POST con JSON",
                "n8n_response_modes": "✅ Compatible con 'Last Node' y 'Respond to Webhook'",
                "formato_respuesta": "JSON estándar (POST) / Texto plano (GET)",
            },
            "instrucciones": {
                "meta_directo": {
                    "paso_1": "Ve a Meta Developers: https://developers.facebook.com/apps",
                    "paso_2": "Selecciona tu app y ve a WhatsApp > Configuration",
                    "paso_3": f"Configura Webhook URL: {webhook_url}",
                    "paso_4": f"Configura Verify Token: (el token de 'webhook_verify_token' configurado)",
                    "paso_5": "Haz clic en 'Verify and Save'",
                    "paso_6": "Suscríbete a eventos: messages, messaging_postbacks",
                },
                "n8n_intermediario": {
                    "descripcion": "n8n recibe de Meta y reenvía a este endpoint",
                    "paso_1": "Crea workflow en n8n con nodo 'Webhook' como trigger",
                    "paso_2": "Configura webhook: HTTP Method = GET y POST, Path = /whatsapp",
                    "paso_3": "Agrega nodo IF: Si hub.mode == 'subscribe', retornar hub.challenge",
                    "paso_4": "Agrega nodo 'HTTP Request': POST a {webhook_url}",
                    "paso_5": "En Meta, configura la URL de n8n como webhook",
                    "paso_6": "n8n reenviará eventos a este endpoint automáticamente",
                },
                "n8n_receptor_final": {
                    "descripcion": "n8n recibe eventos y los procesa completamente",
                    "paso_1": "Crea workflow en n8n con nodo 'Webhook' público",
                    "paso_2": "Copia la URL generada por n8n",
                    "paso_3": "En Meta, configura esa URL como webhook",
                    "paso_4": "Procesa eventos en n8n (filtros, transformaciones, etc.)",
                    "paso_5": "Opcional: Enviar a este endpoint con nodo HTTP Request",
                },
            },
            "ejemplo_n8n_workflow": {
                "nodos": [
                    "1. Webhook (Trigger) - Método: GET y POST",
                    "2. IF (hub.mode == 'subscribe'?)",
                    "3. Respond to Webhook (retornar hub.challenge)",
                    "4. HTTP Request (POST a este endpoint)",
                    "5. Function (procesamiento opcional)",
                ],
                "nota": "El endpoint acepta tanto formato Meta como formato genérico de n8n",
                "formato_aceptado": [
                    "Formato Meta estándar (object: whatsapp_business_account)",
                    "Formato n8n wrapper (body: {...})",
                    "Formato n8n wrapper (data: {...})",
                    "Formato genérico JSON",
                ],
            },
        }

    except Exception as e:
        logger.error(f"❌ Error obteniendo info de webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
