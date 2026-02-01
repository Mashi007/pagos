"""
Servicio para manejar mensajes entrantes de WhatsApp (Meta API)
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from app.schemas.whatsapp import WhatsAppMessage, WhatsAppContact

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Servicio para procesar mensajes de WhatsApp"""
    
    def __init__(self):
        self.logger = logger
    
    async def process_incoming_message(
        self, 
        message: WhatsAppMessage, 
        contact: Optional[WhatsAppContact] = None
    ) -> Dict[str, Any]:
        """
        Procesa un mensaje entrante de WhatsApp
        
        Args:
            message: Mensaje recibido
            contact: Información del contacto (opcional)
            
        Returns:
            Dict con información del procesamiento
        """
        try:
            self.logger.info(
                f"Procesando mensaje de WhatsApp - ID: {message.id}, "
                f"From: {message.from_}, Type: {message.type}"
            )
            
            # Extraer información del mensaje
            message_data = {
                "message_id": message.id,
                "from_number": message.from_,
                "timestamp": message.timestamp,
                "message_type": message.type,
                "processed_at": datetime.utcnow().isoformat()
            }
            
            # Procesar según el tipo de mensaje
            if message.type == "text" and message.text:
                message_data["text_content"] = message.text.body
                result = await self._process_text_message(message.text.body, message.from_)
                message_data.update(result)
            else:
                message_data["status"] = "unsupported_type"
                message_data["note"] = f"Tipo de mensaje {message.type} no soportado aún"
            
            # Información del contacto si está disponible
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
