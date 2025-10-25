# backend/app/services/whatsapp_service.py
"""Servicio para envío de mensajes WhatsApp

Usando Meta Developers API
"""

import logging
import re
from typing import Any, Dict, Optional
import aiohttp

from app.core.config import settings

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Servicio para gestión de WhatsApp usando Meta Developers API"""

    def __init__(self):
        # Configuración de Meta Developers API
        self.api_url = getattr(settings, 'WHATSAPP_API_URL', 'https://graph.facebook.com/v18.0')
        self.access_token = getattr(settings, 'WHATSAPP_ACCESS_TOKEN', None)
        self.phone_number_id = getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', None)
        
        # Verificar configuración
        if not self.access_token or not self.phone_number_id:
            logger.warning("Credenciales de Meta Developers no configuradas")

    async def send_message(
        self,
        to_number: str,
        message: str,
        template_name: Optional[str] = None,
        template_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Enviar mensaje WhatsApp usando Meta Developers API
        
        Args:
            to_number: Número de teléfono destinatario
            message: Mensaje a enviar
            template_name: Nombre del template (opcional)
            template_params: Parámetros del template (opcional)
            
        Returns:
            Dict con resultado del envío
        """
        try:
            if not self.access_token or not self.phone_number_id:
                return {
                    "success": False,
                    "error": "WhatsApp no configurado. Faltan credenciales de Meta",
                    "message_id": None,
                }

            # Formatear número
            clean_number = (
                to_number.replace("+", "").replace(" ", "").replace("-", "")
            )
            
            if not clean_number.isdigit():
                return {
                    "success": False,
                    "error": "Número de teléfono inválido",
                    "message_id": None,
                }

            # URL del endpoint de Meta
            url = f"{self.api_url}/{self.phone_number_id}/messages"

            # Headers
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }

            # Preparar payload
            if template_name and template_params:
                # Mensaje con template
                payload = {
                    "messaging_product": "whatsapp",
                    "to": clean_number,
                    "type": "template",
                    "template": {
                        "name": template_name,
                        "language": {"code": "es"},
                        "components": [
                            {
                                "type": "body",
                                "parameters": [
                                    {"type": "text", "text": str(value)}
                                    for value in template_params.values()
                                ],
                            }
                        ],
                    },
                }
            else:
                # Mensaje simple
                payload = {
                    "messaging_product": "whatsapp",
                    "to": clean_number,
                    "type": "text",
                    "text": {"body": message},
                }

            # Enviar mensaje
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, headers=headers, json=payload
                ) as response:
                    response_data = await response.json()
                    
                    if response.status == 200:
                        message_id = response_data.get("messages", [{}])[0].get("id")
                        
                        logger.info(f"Mensaje WhatsApp enviado: {message_id}")
                        return {
                            "success": True,
                            "message_id": message_id,
                            "status": "sent",
                            "error": None,
                        }
                    else:
                        error_msg = f"Error Meta API: {response_data}"
                        logger.error(error_msg)
                        return {
                            "success": False,
                            "error": error_msg,
                            "message_id": None,
                        }

        except Exception as e:
            error_msg = f"Error enviando WhatsApp: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg, "message_id": None}

    def validate_phone_number(self, phone_number: str) -> bool:
        """
        Validar formato de número de teléfono
        
        Args:
            phone_number: Número a validar
            
        Returns:
            True si es válido
        """
        # Formato esperado: +593999999999 o similar
        pattern = r"^\+\d{10,15}$"
        return bool(re.match(pattern, phone_number))

    def validate_meta_configuration(self) -> Dict[str, Any]:
        """
        Validar configuración de Meta Developers
        
        Returns:
            Dict con estado de la configuración
        """
        config_status = {
            "access_token": bool(self.access_token),
            "phone_number_id": bool(self.phone_number_id),
            "api_url": self.api_url,
        }
        config_status["ready"] = all([
            config_status["access_token"], 
            config_status["phone_number_id"]
        ])
        
        return config_status
