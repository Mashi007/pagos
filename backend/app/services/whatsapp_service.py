"""
Servicio de WhatsApp
"""

import logging
import re
from typing import Any, Dict, Optional

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Servicio para envío de mensajes WhatsApp usando Meta Developers API"""

    def __init__(self, db: Optional[Session] = None):
        """
        Inicializar servicio WhatsApp

        Args:
            db: Sesión de base de datos opcional para leer configuración desde BD
        """
        self.db = db
        self._cargar_configuracion()

    def _cargar_configuracion(self):
        """Cargar configuración desde BD si está disponible, sino usar settings por defecto"""
        # Valores por defecto desde settings
        self.api_url = settings.WHATSAPP_API_URL
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.business_account_id = settings.WHATSAPP_BUSINESS_ACCOUNT_ID
        self.webhook_verify_token = settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN
        self.modo_pruebas = True  # Por defecto: Pruebas (más seguro)
        self.telefono_pruebas = ""

        # Si hay sesión de BD, intentar cargar configuración desde BD
        if self.db:
            try:
                from app.models.configuracion_sistema import ConfiguracionSistema

                configs = self.db.query(ConfiguracionSistema).filter(ConfiguracionSistema.categoria == "WHATSAPP").all()

                if configs:
                    config_dict = {config.clave: config.valor for config in configs}

                    # Actualizar valores si existen en BD
                    if config_dict.get("api_url"):
                        self.api_url = config_dict["api_url"]
                    if config_dict.get("access_token"):
                        self.access_token = config_dict["access_token"]
                    if config_dict.get("phone_number_id"):
                        self.phone_number_id = config_dict["phone_number_id"]
                    if config_dict.get("business_account_id"):
                        self.business_account_id = config_dict["business_account_id"]
                    if config_dict.get("webhook_verify_token"):
                        self.webhook_verify_token = config_dict["webhook_verify_token"]
                    if config_dict.get("modo_pruebas"):
                        self.modo_pruebas = config_dict["modo_pruebas"].lower() in ("true", "1", "yes", "on")
                    if config_dict.get("telefono_pruebas"):
                        self.telefono_pruebas = config_dict["telefono_pruebas"]

                    logger.info("✅ Configuración de WhatsApp cargada desde base de datos")
                    if self.modo_pruebas:
                        logger.warning(f"⚠️ MODO PRUEBAS ACTIVO: Todos los mensajes se enviarán a {self.telefono_pruebas}")
                    return

            except Exception as e:
                logger.warning(f"⚠️ No se pudo cargar configuración de WhatsApp desde BD: {str(e)}. Usando valores por defecto.")

        logger.debug("📱 Usando configuración de WhatsApp por defecto desde settings")

        # Verificar configuración
        if not self.access_token or not self.phone_number_id:
            logger.warning("Credenciales de Meta Developers no configuradas")

    async def send_message(
        self,
        to_number: str,
        message: str,
        template_name: Optional[str] = None,
        forzar_envio_real: bool = False,
    ) -> Dict[str, Any]:
        """
        Enviar mensaje WhatsApp usando Meta Developers API

        Args:
            to_number: Número de teléfono destinatario
            message: Mensaje a enviar
            template_name: Nombre del template (opcional)
            forzar_envio_real: Si True, ignora modo_pruebas y envía al destinatario real.
                              Útil para pruebas de configuración en modo Producción.

        Returns:
            Dict con resultado del envío
        """
        try:
            # Recargar configuración para obtener modo_pruebas actualizado
            self._cargar_configuracion()

            if not self.access_token or not self.phone_number_id:
                return {
                    "success": False,
                    "message": "Credenciales de WhatsApp no configuradas",
                }

            # Formatear número
            clean_number = to_number.replace("+", "").replace(" ", "").replace("-", "")

            # Si está en modo pruebas, redirigir todos los mensajes a telefono_pruebas
            # (excepto si se fuerza envío real, útil para pruebas de configuración)
            numero_destinatario = clean_number
            if self.modo_pruebas and self.telefono_pruebas and not forzar_envio_real:
                numero_original = clean_number
                # Agregar información del destinatario original al mensaje
                message = f"[PRUEBAS - Originalmente para: {numero_original}]\n\n{message}"
                numero_destinatario = self.telefono_pruebas.replace("+", "").replace(" ", "").replace("-", "")
                logger.warning(f"🧪 MODO PRUEBAS: Redirigiendo mensaje de {clean_number} a {self.telefono_pruebas}")

            if not numero_destinatario.isdigit():
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
                    "to": numero_destinatario,
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
                    "to": numero_destinatario,
                    "type": "text",
                    "text": {"body": message},
                }

            # Enviar mensaje
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload)

                if response.status_code == 200:
                    result = response.json()
                    mensaje_exito = "Mensaje enviado exitosamente"
                    if self.modo_pruebas and not forzar_envio_real:
                        mensaje_exito = f"Mensaje enviado exitosamente (MODO PRUEBAS: originalmente para {to_number})"
                    logger.info(f"Mensaje WhatsApp enviado exitosamente a: {numero_destinatario}")
                    return {
                        "success": True,
                        "message": mensaje_exito,
                        "message_id": result.get("messages", [{}])[0].get("id"),
                        "recipient": numero_destinatario,
                        "original_recipient": to_number if self.modo_pruebas and not forzar_envio_real else None,
                        "modo_pruebas": self.modo_pruebas,
                    }
                else:
                    error_data = response.json()
                    logger.error(f"Error enviando mensaje WhatsApp: {error_data}")
                    return {
                        "success": False,
                        "message": f"Error de API: {error_data.get('error', {}).get('message', 'Error desconocido')}",
                        "recipient": numero_destinatario,
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

    async def send_welcome_message(self, phone_number: str, client_name: str) -> Dict[str, Any]:
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
            # Recargar configuración
            self._cargar_configuracion()

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
                    error_data = response.json() if response.content else {}
                    return {
                        "success": False,
                        "message": f"Error de conexión: {response.status_code} - {error_data.get('error', {}).get('message', 'Error desconocido')}",
                    }

        except Exception as e:
            logger.error(f"Error probando conexión WhatsApp: {str(e)}")
            return {"success": False, "message": f"Error de conexión: {str(e)}"}
