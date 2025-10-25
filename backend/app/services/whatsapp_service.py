# backend/app/services/whatsapp_service.py
"""
Servicio para envío de mensajes WhatsApp usando Meta Developers API.
"""
import logging
import re
from datetime import datetime
from typing import Any, Dict, Optional

import aiohttp

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.notificacion import EstadoNotificacion, Notificacion

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Servicio para gestión de WhatsApp usando Meta Developers API"""

    def __init__(self):
        # Configuración de Meta Developers API
        self.api_url = settings.WHATSAPP_API_URL
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.business_account_id = settings.WHATSAPP_BUSINESS_ACCOUNT_ID
        self.webhook_verify_token = settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN

        # Verificar configuración
        if not self.access_token or not self.phone_number_id:
            logger.warning("Credenciales de Meta Developers no configuradas")
            logger.info(
                "Variables requeridas: WHATSAPP_ACCESS_TOKEN, WHATSAPP \
                _PHONE_NUMBER_ID"
            )

    async def send_message(
        self,
        to_number: str,
        message: str,
        template_name: Optional[str] = None,
        template_params: Optional[Dict[str, Any]] = None,
        notificacion_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Enviar mensaje WhatsApp usando Meta Developers API

        Args:
            to_number: Número de teléfono destinatario (formato internacional)
            message: Mensaje a enviar
            template_name: Nombre del template (opcional)
            template_params: Parámetros del template (opcional)
            notificacion_id: ID de notificación para actualizar estado

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

            # Formatear número (quitar + y espacios)
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

            # Preparar payload según tipo de mensaje
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
                        message_id = response_data.get("messages", [{}])[
                            0
                        ].get("id")

                        # Actualizar notificación
                        if notificacion_id:
                            self._actualizar_notificacion(
                                notificacion_id,
                                EstadoNotificacion.ENVIADA.value,
                                message_id=message_id,
                            )

                        logger.info(f"Mensaje WhatsApp enviado: {message_id}")
                        return {
                            "success": True,
                            "message_id": message_id,
                            "status": "sent",
                            "error": None,
                            "response": response_data,
                        }
                    else:
                        error_msg = f"Error Meta API: {response_data}"
                        logger.error(error_msg)

                        # Actualizar notificación como fallida
                        if notificacion_id:
                            self._actualizar_notificacion(
                                notificacion_id,
                                EstadoNotificacion.FALLIDA.value,
                                error=error_msg,
                            )

                        return {
                            "success": False,
                            "error": error_msg,
                            "message_id": None,
                            "response": response_data,
                        }

        except Exception as e:
            error_msg = f"Error enviando WhatsApp: {str(e)}"
            logger.error(error_msg)

            # Actualizar notificación como fallida
            if notificacion_id:
                self._actualizar_notificacion(
                    notificacion_id,
                    EstadoNotificacion.FALLIDA.value,
                    error=error_msg,
                )

            return {"success": False, "error": error_msg, "message_id": None}

    async def send_template_message(
        self,
        to_number: str,
        template_name: str,
        variables: Dict[str, Any],
        notificacion_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Enviar mensaje usando template predefinido de Meta.

        Args:
            to_number: Número destinatario
            template_name: Nombre del template (debe estar aprobado en Meta)
            variables: Variables para el template
            notificacion_id: ID de notificación

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

            # Preparar payload para template
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
                                for value in variables.values()
                            ],
                        }
                    ],
                },
            }

            # Enviar mensaje
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, headers=headers, json=payload
                ) as response:
                    response_data = await response.json()

                    if response.status == 200:
                        message_id = response_data.get("messages", [{}])[
                            0
                        ].get("id")

                        # Actualizar notificación
                        if notificacion_id:
                            self._actualizar_notificacion(
                                notificacion_id,
                                EstadoNotificacion.ENVIADA.value,
                                message_id=message_id,
                            )

                        logger.info(f"Template WhatsApp enviado: {message_id}")
                        return {
                            "success": True,
                            "message_id": message_id,
                            "status": "sent",
                            "error": None,
                            "response": response_data,
                        }
                    else:
                        error_msg = f"Error Meta API template: {response_data}"
                        logger.error(error_msg)

                        # Actualizar notificación como fallida
                        if notificacion_id:
                            self._actualizar_notificacion(
                                notificacion_id,
                                EstadoNotificacion.FALLIDA.value,
                                error=error_msg,
                            )

                        return {
                            "success": False,
                            "error": error_msg,
                            "message_id": None,
                            "response": response_data,
                        }

        except Exception as e:
            error_msg = f"Error enviando template WhatsApp: {str(e)}"
            logger.error(error_msg)

            # Actualizar notificación como fallida
            if notificacion_id:
                self._actualizar_notificacion(
                    notificacion_id,
                    EstadoNotificacion.FALLIDA.value,
                    error=error_msg,
                )

            return {"success": False, "error": error_msg, "message_id": None}

    def get_message_status(self, message_id: str) -> Dict[str, Any]:
        """
        Obtener estado de un mensaje enviado usando Meta API.

        Args:
            message_id: ID del mensaje de Meta

        Returns:
            Dict con información del mensaje
        """
        try:
            if not self.access_token or not self.phone_number_id:
                return {"error": "Credenciales no configuradas"}

            # URL para obtener estado del mensaje
            f"{self.api_url}/{self.phone_number_id}/messages/{message_id}"

            # Nota: Meta API no proporciona endpoint directo para consultar estado
            # El estado se maneja via webhooks
            return {
                "message_id": message_id,
                "note": "Estado se obtiene via webhooks de Meta",
                "status": "unknown",
            }

        except Exception as e:
            logger.error(
                f"Error obteniendo estado del mensaje {message_id}: {str(e)}"
            )
            return {"error": str(e)}

    def _actualizar_notificacion(
        self,
        notificacion_id: int,
        estado: str,
        message_id: Optional[str] = None,
        error: Optional[str] = None,
    ):
        """
        Actualizar estado de notificación en base de datos.
        """
        try:
            db = SessionLocal()
            notificacion = (
                db.query(Notificacion)
                .filter(Notificacion.id == notificacion_id)
                .first()
            )

            if notificacion:
                notificacion.estado = estado
                notificacion.enviada_en = datetime.now()

                if message_id:
                    # Guardar ID de Meta en metadata
                    if not notificacion.meta_info:
                        notificacion.meta_info = {}
                    notificacion.meta_info["meta_message_id"] = message_id

                if error:
                    notificacion.error = error

                db.commit()

        except Exception as e:
            logger.error(
                f"Error actualizando notificación {notificacion_id}: {str(e)}"
            )
        finally:
            db.close()

    def validate_phone_number(self, phone_number: str) -> bool:
        """
        Validar formato de número de teléfono.

        Args:
            phone_number: Número a validar

        Returns:
            True si es válido
        """

        # Formato esperado: +593999999999 (Ecuador) o similar
        pattern = r"^\+\d{10,15}$"
        return bool(re.match(pattern, phone_number))

    def validate_meta_configuration(self) -> Dict[str, Any]:
        """
        Validar configuración de Meta Developers.

        Returns:
            Dict con estado de la configuración
        """
        config_status = {
            "access_token": bool(self.access_token),
            "phone_number_id": bool(self.phone_number_id),
            "business_account_id": bool(self.business_account_id),
            "webhook_verify_token": bool(self.webhook_verify_token),
            "api_url": self.api_url,
        }

        config_status["ready"] = all(
            [config_status["access_token"], config_status["phone_number_id"]]
        )

        return config_status
