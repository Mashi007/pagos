"""
Servicio para manejar mensajes entrantes de WhatsApp (Meta API).
Si reciben imagen, se guarda en BD tabla pagos_whatsapp (fecha, cedula_cliente, imagen).
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.schemas.whatsapp import WhatsAppMessage, WhatsAppContact
from app.core.whatsapp_config_holder import get_whatsapp_config, sync_from_db as whatsapp_sync_from_db
from app.models.cliente import Cliente
from app.models.pagos_whatsapp import PagosWhatsapp

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Servicio para procesar mensajes de WhatsApp"""
    
    def __init__(self):
        self.logger = logger
    
    async def process_incoming_message(
        self, 
        message: WhatsAppMessage, 
        contact: Optional[WhatsAppContact] = None,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Procesa un mensaje entrante de WhatsApp.
        Si es imagen, descarga y guarda en pagos_whatsapp (fecha, cedula_cliente, imagen).
        """
        try:
            self.logger.info(
                f"Procesando mensaje de WhatsApp - ID: {message.id}, "
                f"From: {message.from_}, Type: {message.type}"
            )
            
            message_data = {
                "message_id": message.id,
                "from_number": message.from_,
                "timestamp": message.timestamp,
                "message_type": message.type,
                "processed_at": datetime.utcnow().isoformat()
            }
            
            if message.type == "text" and message.text:
                message_data["text_content"] = message.text.body
                result = await self._process_text_message(message.text.body, message.from_)
                message_data.update(result)
            elif message.type == "image" and message.image and db:
                result = await self._process_image_message(message, db)
                message_data.update(result)
            else:
                message_data["status"] = "unsupported_type"
                message_data["note"] = f"Tipo de mensaje {message.type} no soportado aún"
            
            if contact:
                message_data["contact_wa_id"] = contact.wa_id
                if contact.profile:
                    message_data["contact_name"] = contact.profile.get("name")
            
            self.logger.info(f"Mensaje procesado exitosamente - ID: {message.id}")
            return {
                "success": True,
                "message_id": message.id,
                "data": message_data
            }
            
        except Exception as e:
            self.logger.error(f"Error procesando mensaje de WhatsApp: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message_id": message.id if message else None
            }
    
    async def _process_image_message(self, message: WhatsAppMessage, db: Session) -> Dict[str, Any]:
        """Descarga la imagen de Meta, obtiene cedula por telefono y guarda en pagos_whatsapp."""
        cedula_cliente = None
        from_number = "".join(c for c in message.from_ if c.isdigit())
        if from_number:
            last_digits = from_number[-10:] if len(from_number) >= 10 else from_number
            q = select(Cliente.cedula).where(
                Cliente.telefono.isnot(None),
                Cliente.telefono.like(f"%{last_digits}")
            ).limit(1)
            row = db.execute(q).scalars().first()
            if row:
                cedula_cliente = row
        whatsapp_sync_from_db()
        cfg = get_whatsapp_config()
        token = (cfg.get("access_token") or "").strip()
        api_url = (cfg.get("api_url") or "https://graph.facebook.com/v18.0").rstrip("/")
        if not token:
            logger.warning("Access token WhatsApp no configurado; no se puede descargar imagen. Configura en Configuración > WhatsApp.")
            return {"status": "image_skipped", "note": "Token no configurado"}
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.get(f"{api_url}/{message.image.id}", headers={"Authorization": f"Bearer {token}"})
                r.raise_for_status()
                data = r.json()
                media_url = data.get("url")
                if not media_url:
                    return {"status": "image_no_url", "note": "Meta no devolvió URL"}
                r2 = await client.get(media_url, headers={"Authorization": f"Bearer {token}"})
                r2.raise_for_status()
                image_bytes = r2.content
            if not image_bytes:
                return {"status": "image_empty", "note": "Imagen vacía"}
            row = PagosWhatsapp(
                fecha=datetime.utcnow(),
                cedula_cliente=cedula_cliente,
                imagen=image_bytes,
            )
            db.add(row)
            db.commit()
            logger.info(f"Imagen guardada en pagos_whatsapp id={row.id} cedula={cedula_cliente}")
            return {"status": "image_saved", "pagos_whatsapp_id": row.id, "cedula_cliente": cedula_cliente}
        except Exception as e:
            logger.exception("Error guardando imagen en pagos_whatsapp: %s", e)
            db.rollback()
            return {"status": "image_error", "note": str(e)}
    
    async def _process_text_message(self, text: str, from_number: str) -> Dict[str, Any]:
        """
        Procesa un mensaje de texto específico
        
        Args:
            text: Contenido del mensaje
            from_number: Número de teléfono remitente
            
        Returns:
            Dict con resultado del procesamiento
        """
        # Normalizar el texto
        text_lower = text.strip().lower()
        
        # Aquí puedes agregar lógica específica para procesar comandos o mensajes
        # Por ejemplo:
        # - Comandos como "SALDO", "PAGO", "ESTADO"
        # - Respuestas automáticas
        # - Integración con otros servicios
        
        result = {
            "status": "processed",
            "command": None,
            "response_needed": False
        }
        
        # Ejemplo: Detectar comandos comunes
        if text_lower.startswith("saldo"):
            result["command"] = "check_balance"
            result["response_needed"] = True
        elif text_lower.startswith("pago"):
            result["command"] = "payment_info"
            result["response_needed"] = True
        elif text_lower.startswith("estado"):
            result["command"] = "check_status"
            result["response_needed"] = True
        
        return result
    
    async def validate_webhook_token(self, verify_token: str, expected_token: str) -> bool:
        """
        Valida el token de verificación del webhook
        
        Args:
            verify_token: Token recibido en el webhook
            expected_token: Token esperado configurado
            
        Returns:
            True si el token es válido
        """
        return verify_token == expected_token
    
    def extract_message_data(self, webhook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extrae datos del mensaje del payload del webhook
        
        Args:
            webhook_data: Datos del webhook de Meta
            
        Returns:
            Dict con mensajes y contactos extraídos, o None si no hay mensajes
        """
        try:
            if not webhook_data.get("entry"):
                return None
            
            messages_data = []
            
            for entry in webhook_data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    
                    # Procesar mensajes entrantes
                    if value.get("messages"):
                        for message in value["messages"]:
                            messages_data.append({
                                "message": message,
                                "metadata": value.get("metadata", {}),
                                "entry_id": entry.get("id")
                            })
                    
                    # Procesar estados de mensajes (si es necesario)
                    if value.get("statuses"):
                        for status in value["statuses"]:
                            self.logger.info(
                                f"Estado de mensaje recibido - ID: {status.get('id')}, "
                                f"Status: {status.get('status')}"
                            )
            
            return {
                "messages": messages_data,
                "has_messages": len(messages_data) > 0
            } if messages_data else None
            
        except Exception as e:
            self.logger.error(f"Error extrayendo datos del webhook: {str(e)}", exc_info=True)
            return None
