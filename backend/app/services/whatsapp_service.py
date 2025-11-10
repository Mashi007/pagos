"""
Servicio de WhatsApp
Cumple con políticas de Meta WhatsApp Business API
"""

import asyncio
import logging
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings

logger = logging.getLogger(__name__)

# Rate limiting: Meta permite 1000 mensajes/día y 80 mensajes/segundo por defecto
# Para producción, estos valores deben ajustarse según el tier de la cuenta
META_RATE_LIMIT_DAILY = 1000  # Mensajes por día
META_RATE_LIMIT_SECOND = 80  # Mensajes por segundo
META_REQUEST_TIMEOUT = 30  # Timeout en segundos para requests HTTP
META_MAX_RETRIES = 3  # Número máximo de reintentos
META_RETRY_BACKOFF_BASE = 2  # Base para backoff exponencial (segundos)


class WhatsAppService:
    """
    Servicio para envío de mensajes WhatsApp usando Meta Developers API
    Cumple con políticas de Meta:
    - Rate limiting (1000/día, 80/segundo)
    - Manejo de errores específicos (429, 403, 400)
    - Retry con backoff exponencial
    - Timeout configurable
    - Logging de compliance
    """

    # Rate limiting en memoria (para producción, usar Redis)
    _rate_limit_daily: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"count": 0, "reset_time": None})
    _rate_limit_second: Dict[str, float] = defaultdict(float)
    _lock = asyncio.Lock()

    def __init__(self, db: Optional[Session] = None):
        """
        Inicializar servicio WhatsApp

        Args:
            db: Sesión de base de datos opcional para leer configuración desde BD
        """
        self.db = db
        self._cargar_configuracion()
        self.timeout = META_REQUEST_TIMEOUT

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
                logger.warning(
                    f"⚠️ No se pudo cargar configuración de WhatsApp desde BD: {str(e)}. Usando valores por defecto."
                )

        logger.debug("📱 Usando configuración de WhatsApp por defecto desde settings")

        # Verificar configuración
        if not self.access_token or not self.phone_number_id:
            logger.warning("Credenciales de Meta Developers no configuradas")

    async def _check_rate_limit(self) -> Dict[str, Any]:
        """
        Verificar rate limits de Meta
        Returns: Dict con success y message si hay error
        """
        async with self._lock:
            now = time.time()
            today = datetime.now().date().isoformat()

            # Verificar límite diario
            daily_limit = self._rate_limit_daily[today]
            if daily_limit["reset_time"] is None:
                daily_limit["reset_time"] = datetime.now() + timedelta(days=1)

            if daily_limit["count"] >= META_RATE_LIMIT_DAILY:
                reset_time = daily_limit["reset_time"]
                return {
                    "success": False,
                    "message": f"Rate limit diario alcanzado ({META_RATE_LIMIT_DAILY} mensajes/día). Reset: {reset_time}",
                    "error_code": "RATE_LIMIT_DAILY",
                }

            # Verificar límite por segundo
            second_key = int(now)
            if self._rate_limit_second[second_key] >= META_RATE_LIMIT_SECOND:
                return {
                    "success": False,
                    "message": f"Rate limit por segundo alcanzado ({META_RATE_LIMIT_SECOND} mensajes/segundo)",
                    "error_code": "RATE_LIMIT_SECOND",
                }

            # Limpiar contadores antiguos (más de 1 segundo)
            keys_to_remove = [k for k in self._rate_limit_second.keys() if k < second_key - 1]
            for k in keys_to_remove:
                del self._rate_limit_second[k]

            # Incrementar contadores
            daily_limit["count"] += 1
            self._rate_limit_second[second_key] += 1

            return {"success": True}

    def _handle_meta_error(self, status_code: int, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Manejar errores específicos de Meta según políticas
        """
        error_info = error_data.get("error", {})
        error_code = error_info.get("code", status_code)
        error_message = error_info.get("message", "Error desconocido")
        error_type = error_info.get("type", "Unknown")

        # Códigos de error específicos de Meta
        if status_code == 429:
            # Rate limit excedido
            retry_after = error_info.get("error_subcode") or 60  # Segundos a esperar
            logger.warning(f"⚠️ Rate limit de Meta alcanzado. Esperar {retry_after}s")
            return {
                "success": False,
                "message": f"Rate limit excedido. Intente nuevamente en {retry_after} segundos",
                "error_code": "META_RATE_LIMIT",
                "retry_after": retry_after,
                "retryable": True,
            }
        elif status_code == 403:
            # Prohibido - puede ser política violada, token inválido, etc.
            logger.error(f"❌ Acceso prohibido por Meta: {error_message} (Tipo: {error_type})")
            return {
                "success": False,
                "message": f"Acceso prohibido: {error_message}",
                "error_code": "META_FORBIDDEN",
                "retryable": False,
            }
        elif status_code == 400:
            # Bad request - validación fallida
            logger.error(f"❌ Solicitud inválida a Meta: {error_message}")
            return {
                "success": False,
                "message": f"Solicitud inválida: {error_message}",
                "error_code": "META_BAD_REQUEST",
                "retryable": False,
            }
        elif status_code == 401:
            # No autorizado - token inválido
            logger.error(f"❌ Token de Meta inválido o expirado")
            return {
                "success": False,
                "message": "Token de acceso inválido o expirado",
                "error_code": "META_UNAUTHORIZED",
                "retryable": False,
            }
        elif status_code >= 500:
            # Errores del servidor de Meta - retryable
            logger.warning(f"⚠️ Error del servidor de Meta ({status_code}): {error_message}")
            return {
                "success": False,
                "message": f"Error temporal del servidor: {error_message}",
                "error_code": "META_SERVER_ERROR",
                "retryable": True,
            }
        else:
            # Otros errores
            logger.error(f"❌ Error de Meta ({status_code}): {error_message}")
            return {
                "success": False,
                "message": f"Error de API: {error_message}",
                "error_code": f"META_ERROR_{status_code}",
                "retryable": status_code >= 500,
            }

    async def _send_with_retry(
        self, url: str, headers: Dict[str, str], payload: Dict[str, Any], max_retries: int = META_MAX_RETRIES
    ) -> httpx.Response:
        """
        Enviar request con retry y backoff exponencial
        """
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, headers=headers, json=payload)

                    # Si es exitoso, retornar
                    if response.status_code == 200:
                        return response

                    # Si no es retryable, retornar inmediatamente
                    error_data = response.json() if response.content else {}
                    error_result = self._handle_meta_error(response.status_code, error_data)

                    if not error_result.get("retryable", False):
                        return response

                    # Si es el último intento, retornar
                    if attempt >= max_retries:
                        return response

                    # Calcular backoff exponencial
                    backoff_time = META_RETRY_BACKOFF_BASE**attempt
                    if "retry_after" in error_result:
                        backoff_time = error_result["retry_after"]

                    logger.info(f"🔄 Reintentando en {backoff_time}s (intento {attempt + 1}/{max_retries + 1})")
                    await asyncio.sleep(backoff_time)
                    last_error = error_result

            except httpx.TimeoutException:
                if attempt >= max_retries:
                    raise
                backoff_time = META_RETRY_BACKOFF_BASE**attempt
                logger.warning(f"⏱️ Timeout. Reintentando en {backoff_time}s")
                await asyncio.sleep(backoff_time)
            except Exception as e:
                if attempt >= max_retries:
                    raise
                backoff_time = META_RETRY_BACKOFF_BASE**attempt
                logger.warning(f"⚠️ Error de conexión: {str(e)}. Reintentando en {backoff_time}s")
                await asyncio.sleep(backoff_time)
                last_error = {"message": str(e)}

        # Si llegamos aquí, todos los reintentos fallaron
        raise Exception(f"Todos los reintentos fallaron. Último error: {last_error}")

    async def send_message(
        self,
        to_number: str,
        message: str,
        template_name: Optional[str] = None,
        forzar_envio_real: bool = False,
    ) -> Dict[str, Any]:
        """
        Enviar mensaje WhatsApp usando Meta Developers API
        Cumple con políticas de Meta: rate limiting, retry, manejo de errores

        Args:
            to_number: Número de teléfono destinatario
            message: Mensaje a enviar
            template_name: Nombre del template (opcional, debe estar aprobado por Meta)
            forzar_envio_real: Si True, ignora modo_pruebas y envía al destinatario real.
                              Útil para pruebas de configuración en modo Producción.

        Returns:
            Dict con resultado del envío
        """
        start_time = time.time()
        try:
            # Recargar configuración para obtener modo_pruebas actualizado
            self._cargar_configuracion()

            if not self.access_token or not self.phone_number_id:
                return {
                    "success": False,
                    "message": "Credenciales de WhatsApp no configuradas",
                    "error_code": "CONFIG_MISSING",
                }

            # Verificar rate limits ANTES de enviar
            rate_check = await self._check_rate_limit()
            if not rate_check["success"]:
                logger.warning(f"⚠️ Rate limit alcanzado: {rate_check.get('message')}")
                return {
                    "success": False,
                    "message": rate_check.get("message", "Rate limit alcanzado"),
                    "error_code": rate_check.get("error_code", "RATE_LIMIT"),
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
                return {"success": False, "message": "Número de teléfono inválido", "error_code": "INVALID_PHONE"}

            # Validar longitud del mensaje (Meta limita a 4096 caracteres)
            if len(message) > 4096:
                logger.error(f"❌ Mensaje excede límite de Meta (4096 caracteres): {len(message)} caracteres")
                return {
                    "success": False,
                    "message": f"Mensaje excede límite de Meta (4096 caracteres). Actual: {len(message)}",
                    "error_code": "MESSAGE_TOO_LONG",
                }

            # URL del endpoint de Meta
            url = f"{self.api_url}/{self.phone_number_id}/messages"

            # Headers
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }

            # Payload del mensaje
            if template_name:
                # Mensaje con template (debe estar aprobado por Meta)
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
                # Logging de compliance: uso de template
                logger.info(f"📋 [COMPLIANCE] Enviando template '{template_name}' a {numero_destinatario}")
            else:
                # Mensaje de texto simple (solo dentro de ventana de 24h)
                payload = {
                    "messaging_product": "whatsapp",
                    "to": numero_destinatario,
                    "type": "text",
                    "text": {"body": message},
                }
                # Logging de compliance: mensaje fuera de template
                logger.info(f"💬 [COMPLIANCE] Enviando mensaje de texto libre a {numero_destinatario}")

            # Enviar mensaje con retry
            response = await self._send_with_retry(url, headers, payload)

            # Procesar respuesta
            if response.status_code == 200:
                result = response.json()
                mensaje_exito = "Mensaje enviado exitosamente"
                if self.modo_pruebas and not forzar_envio_real:
                    mensaje_exito = f"Mensaje enviado exitosamente (MODO PRUEBAS: originalmente para {to_number})"

                message_id = result.get("messages", [{}])[0].get("id")
                elapsed_time = time.time() - start_time

                # Logging de compliance: envío exitoso
                logger.info(
                    f"✅ [COMPLIANCE] Mensaje WhatsApp enviado exitosamente a {numero_destinatario} "
                    f"(ID: {message_id}, Tiempo: {elapsed_time:.2f}s)"
                )

                # Construir mensaje de respuesta que incluya el message_id para búsqueda posterior
                respuesta_servicio = f"Mensaje enviado exitosamente. Message ID: {message_id}" if message_id else mensaje_exito

                return {
                    "success": True,
                    "message": mensaje_exito,
                    "message_id": message_id,
                    "recipient": numero_destinatario,
                    "original_recipient": to_number if self.modo_pruebas and not forzar_envio_real else None,
                    "modo_pruebas": self.modo_pruebas,
                    "elapsed_time": elapsed_time,
                    "respuesta_servicio": respuesta_servicio,  # Incluir para búsqueda en webhooks
                }
            else:
                # Manejar error específico de Meta
                error_data = response.json() if response.content else {}
                error_result = self._handle_meta_error(response.status_code, error_data)

                # Logging de compliance: error
                logger.error(
                    f"❌ [COMPLIANCE] Error enviando mensaje WhatsApp a {numero_destinatario}: "
                    f"{error_result.get('message')} (Código: {error_result.get('error_code')})"
                )

                return {
                    "success": False,
                    "message": error_result.get("message", "Error desconocido"),
                    "error_code": error_result.get("error_code", "UNKNOWN_ERROR"),
                    "recipient": numero_destinatario,
                    "retryable": error_result.get("retryable", False),
                }

        except httpx.TimeoutException:
            elapsed_time = time.time() - start_time
            logger.error(f"⏱️ [COMPLIANCE] Timeout enviando mensaje WhatsApp a {to_number} (Tiempo: {elapsed_time:.2f}s)")
            return {
                "success": False,
                "message": f"Timeout al enviar mensaje (límite: {self.timeout}s)",
                "error_code": "TIMEOUT",
                "recipient": to_number,
            }
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(
                f"❌ [COMPLIANCE] Error enviando mensaje WhatsApp a {to_number}: {str(e)} (Tiempo: {elapsed_time:.2f}s)"
            )
            return {
                "success": False,
                "message": f"Error enviando mensaje: {str(e)}",
                "error_code": "EXCEPTION",
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

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    return {
                        "success": True,
                        "message": "Conexión exitosa con Meta Developers API",
                    }
                else:
                    error_data = response.json() if response.content else {}
                    error_result = self._handle_meta_error(response.status_code, error_data)
                    return {
                        "success": False,
                        "message": error_result.get("message", f"Error de conexión: {response.status_code}"),
                        "error_code": error_result.get("error_code", "CONNECTION_ERROR"),
                    }

        except Exception as e:
            logger.error(f"Error probando conexión WhatsApp: {str(e)}")
            return {"success": False, "message": f"Error de conexión: {str(e)}"}
