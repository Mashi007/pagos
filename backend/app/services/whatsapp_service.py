"""
Servicio de WhatsApp
"""

import logging
import re
from typing import Dict, Any, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Servicio para envío de mensajes WhatsApp usando Meta Developers API"""

    def __init__(self):
        """Inicializar servicio WhatsApp"""
        self.api_url = settings.WHATSAPP_API_URL
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID

        # Verificar configuración
        if not self.access_token or not self.phone_number_id:
            logger.warning("Credenciales de Meta Developers no configuradas")

    async def send_message(
        self, to_number: str, message: str, template_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enviar mensaje WhatsApp usando Meta Developers API

        Args:
            to_number: Número de teléfono destinatario
            message: Mensaje a enviar
            template_name: Nombre del template (opcional)

        Returns:
            Dict con resultado del envío
        """
        try:
            if not self.access_token or not self.phone_number_id:
                return {
                    "success": False,
                    "message": "Credenciales de WhatsApp no configuradas",
                }

            # Formatear número
            clean_number = to_number.replace("+", "").replace(" ", "").replace("-", "")

            if not clean_number.isdigit():
                return {"success": False, "message": "Número de teléfono inválido"}

            # URL del endpoint de Meta
            url = f"{self.api_url}/{self.phone_number_id}/messages"

            # Headers
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }

            # Payload del mensaje
            if template_name:
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
                                "parameters": [{"type": "text", "text": message}],
                            }
                        ],
                    },
                }
            else:
                # Mensaje de texto simple
                payload = {
                    "messaging_product": "whatsapp",
                    "to": clean_number,
                    "type": "text",
                    "text": {"body": message},
                }

            # Enviar mensaje
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload)

                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Mensaje WhatsApp enviado exitosamente a: {to_number}")
                    return {
                        "success": True,
                        "message": "Mensaje enviado exitosamente",
                        "message_id": result.get("messages", [{}])[0].get("id"),
                        "recipient": to_number,
                    }
                else:
                    error_data = response.json()
                    logger.error(f"Error enviando mensaje WhatsApp: {error_data}")
                    return {
                        "success": False,
                        "message": f"Error de API: {error_data.get('error', {}).get('message', 'Error desconocido')}",
                        "recipient": to_number,
                    }

        except Exception as e:
            logger.error(f"Error enviando mensaje WhatsApp: {str(e)}")
            return {
                "success": False,
                "message": f"Error enviando mensaje: {str(e)}",
                "recipient": to_number,
            }

    async def send_payment_reminder(
        self, phone_number: str, client_name: str, loan_amount: float, due_date: str
    ) -> Dict[str, Any]:
        """
        Enviar recordatorio de pago por WhatsApp

        Args:
            phone_number: Número de teléfono del cliente
            client_name: Nombre del cliente
            loan_amount: Monto del préstamo
            due_date: Fecha de vencimiento

        Returns:
            Dict con resultado del envío
        """
        message = f"""
Hola {client_name},

Te recordamos que tienes un pago pendiente:

💰 Monto: ${loan_amount:,.2f}
📅 Fecha de vencimiento: {due_date}

Por favor realiza tu pago a tiempo para evitar cargos adicionales.

Saludos,
Equipo de {settings.APP_NAME}
        """.strip()

        return await self.send_message(phone_number, message)

    async def send_welcome_message(
        self, phone_number: str, client_name: str
    ) -> Dict[str, Any]:
        """
        Enviar mensaje de bienvenida por WhatsApp

        Args:
            phone_number: Número de teléfono del cliente
            client_name: Nombre del cliente

        Returns:
            Dict con resultado del envío
        """
        message = f"""
¡Hola {client_name}!

Bienvenido a {settings.APP_NAME}. 

Tu cuenta ha sido creada exitosamente. Ahora puedes acceder a nuestros servicios de préstamos.

Si tienes alguna pregunta, no dudes en contactarnos.

Saludos,
Equipo de {settings.APP_NAME}
        """.strip()

        return await self.send_message(phone_number, message)

    def validate_phone_number(self, phone_number: str) -> bool:
        """
        Validar formato de número de teléfono

        Args:
            phone_number: Número de teléfono a validar

        Returns:
            bool: True si es válido
        """
        # Patrón para números de teléfono internacionales
        pattern = r"^\+?[1-9]\d{1,14}$"
        return bool(re.match(pattern, phone_number))

    async def test_connection(self) -> Dict[str, Any]:
        """
        Probar conexión con Meta Developers API

        Returns:
            Dict con resultado de la prueba
        """
        try:
            if not self.access_token or not self.phone_number_id:
                return {"success": False, "message": "Credenciales no configuradas"}

            # URL para obtener información del número de teléfono
            url = f"{self.api_url}/{self.phone_number_id}"

            headers = {
                "Authorization": f"Bearer {self.access_token}",
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    return {
                        "success": True,
                        "message": "Conexión exitosa con Meta Developers API",
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Error de conexión: {response.status_code}",
                    }

        except Exception as e:
            logger.error(f"Error probando conexión WhatsApp: {str(e)}")
            return {"success": False, "message": f"Error de conexión: {str(e)}"}
