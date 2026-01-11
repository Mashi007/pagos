"""
Servicio de Bot de WhatsApp
Procesa mensajes recibidos y genera respuestas automáticas
"""

import logging
from datetime import datetime
from typing import Dict, Optional

from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.conversacion_whatsapp import ConversacionWhatsApp
from app.services.whatsapp_service import WhatsAppService

logger = logging.getLogger(__name__)


class WhatsAppBotService:
    """
    Servicio para procesar mensajes de WhatsApp y generar respuestas automáticas
    """

    def __init__(self, db: Session):
        self.db = db
        self.whatsapp_service = WhatsAppService(db=db)

    async def procesar_mensaje_recibido(
        self,
        from_number: str,
        message_id: str,
        message_type: str,
        body: str,
        timestamp: int,
        to_number: Optional[str] = None,
    ) -> Dict[str, any]:
        """
        Procesar mensaje recibido de un cliente

        Args:
            from_number: Número que envía el mensaje
            message_id: ID del mensaje en Meta
            message_type: Tipo de mensaje (text, image, etc.)
            body: Contenido del mensaje
            timestamp: Timestamp de Meta (Unix timestamp)
            to_number: Número que recibe (opcional, se obtiene de configuración)

        Returns:
            Dict con resultado del procesamiento
        """
        try:
            # Obtener número de destino si no se proporciona
            if not to_number:
                to_number = self.whatsapp_service.phone_number_id

            # Convertir timestamp de Meta (Unix) a datetime
            timestamp_dt = datetime.fromtimestamp(int(timestamp))

            # Buscar cliente por número de teléfono
            cliente = self._buscar_cliente_por_telefono(from_number)

            # Guardar mensaje en BD
            conversacion = ConversacionWhatsApp(
                message_id=message_id,
                from_number=from_number,
                to_number=to_number,
                message_type=message_type,
                body=body,
                timestamp=timestamp_dt,
                direccion="INBOUND",
                cliente_id=cliente.id if cliente else None,
                procesado=False,
                respuesta_enviada=False,
            )
            self.db.add(conversacion)
            self.db.commit()
            self.db.refresh(conversacion)

            logger.info(
                f"📨 Mensaje recibido guardado: ID {conversacion.id} de {from_number} "
                f"(Cliente: {cliente.id if cliente else 'No encontrado'})"
            )

            # Procesar mensaje y generar respuesta
            respuesta = await self._generar_respuesta(conversacion, cliente)

            # Actualizar conversación
            conversacion.procesado = True
            conversacion.respuesta_bot = respuesta.get("mensaje", "")
            self.db.commit()

            # Enviar respuesta si se generó
            if respuesta.get("enviar", False):
                resultado_envio = await self._enviar_respuesta(
                    to_number=from_number,
                    mensaje=respuesta["mensaje"],
                    conversacion_id=conversacion.id,
                )

                if resultado_envio.get("success"):
                    conversacion.respuesta_enviada = True
                    conversacion.respuesta_meta_id = resultado_envio.get("message_id")
                    self.db.commit()
                    logger.info(f"✅ Respuesta enviada a {from_number}")
                else:
                    conversacion.error = resultado_envio.get("message", "Error desconocido")
                    self.db.commit()
                    logger.error(f"❌ Error enviando respuesta: {resultado_envio.get('message')}")

            return {
                "success": True,
                "conversacion_id": conversacion.id,
                "cliente_encontrado": cliente is not None,
                "respuesta_enviada": conversacion.respuesta_enviada,
            }

        except Exception as e:
            logger.error(f"❌ Error procesando mensaje recibido: {e}", exc_info=True)
            self.db.rollback()
            return {"success": False, "error": str(e)}

    def _buscar_cliente_por_telefono(self, telefono: str) -> Optional[Cliente]:
        """
        Buscar cliente por número de teléfono

        Args:
            telefono: Número de teléfono (puede tener + o no)

        Returns:
            Cliente si se encuentra, None si no
        """
        try:
            # Limpiar número (remover +, espacios, guiones)
            telefono_limpio = telefono.replace("+", "").replace(" ", "").replace("-", "")

            # Buscar cliente por teléfono exacto
            cliente = self.db.query(Cliente).filter(Cliente.telefono == telefono_limpio).first()

            if not cliente:
                # Intentar buscar sin código de país (últimos 10 dígitos)
                if len(telefono_limpio) > 10:
                    telefono_sin_codigo = telefono_limpio[-10:]
                    cliente = self.db.query(Cliente).filter(Cliente.telefono.like(f"%{telefono_sin_codigo}")).first()

            return cliente

        except Exception as e:
            logger.error(f"Error buscando cliente por teléfono {telefono}: {e}")
            return None

    async def _generar_respuesta(self, conversacion: ConversacionWhatsApp, cliente: Optional[Cliente]) -> Dict[str, any]:
        """
        Generar respuesta automática para un mensaje

        Args:
            conversacion: Conversación recibida
            cliente: Cliente que envió el mensaje (si se encontró)

        Returns:
            Dict con mensaje y si debe enviarse
        """
        mensaje = conversacion.body.lower().strip() if conversacion.body else ""

        # Saludos básicos
        saludos = ["hola", "buenos días", "buenas tardes", "buenas noches", "hi", "hello"]
        if any(saludo in mensaje for saludo in saludos):
            if cliente:
                return {
                    "mensaje": f"¡Hola {cliente.nombres}! 👋\n\nSoy el asistente virtual de RAPICREDIT. ¿En qué puedo ayudarte?\n\nPuedes preguntarme sobre:\n• Estado de tu préstamo\n• Cuotas pendientes\n• Pagos realizados\n• Información de tu cuenta",
                    "enviar": True,
                }
            else:
                return {
                    "mensaje": "¡Hola! 👋\n\nSoy el asistente virtual de RAPICREDIT. Para ayudarte mejor, necesito que me envíes tu número de cédula.",
                    "enviar": True,
                }

        # Comandos de consulta
        if "cedula" in mensaje or "cédula" in mensaje or "documento" in mensaje:
            return {
                "mensaje": "Por favor, envíame tu número de cédula para consultar tu información.",
                "enviar": True,
            }

        # Si hay cliente, usar Chat AI para respuesta inteligente
        if cliente:
            try:
                respuesta_ai = await self._consultar_chat_ai(mensaje, cliente)
                if respuesta_ai:
                    return {"mensaje": respuesta_ai, "enviar": True}
            except Exception as e:
                logger.warning(f"Error consultando Chat AI: {e}")

        # Respuesta por defecto
        if cliente:
            return {
                "mensaje": f"Hola {cliente.nombres}, recibí tu mensaje. ¿En qué puedo ayudarte?\n\nPuedes preguntarme sobre tu préstamo, cuotas o pagos.",
                "enviar": True,
            }
        else:
            return {
                "mensaje": "Hola, recibí tu mensaje. Para ayudarte mejor, por favor envíame tu número de cédula.",
                "enviar": True,
            }

    async def _consultar_chat_ai(self, pregunta: str, cliente: Cliente) -> Optional[str]:
        """
        Consultar Chat AI para respuesta inteligente

        Args:
            pregunta: Pregunta del cliente
            cliente: Cliente que pregunta

        Returns:
            Respuesta del Chat AI o None si hay error
        """
        try:
            from app.api.v1.endpoints.configuracion import _obtener_configuracion_ai_con_reintento, _validar_configuracion_ai
            from app.services.ai_chat_service import AIChatService

            # Verificar que la configuración AI esté activa
            configs = _obtener_configuracion_ai_con_reintento(self.db)
            if not configs:
                logger.debug("Configuración AI no encontrada, usando respuestas básicas")
                return None

            config_dict = {config.clave: config.valor for config in configs}

            # Verificar que AI esté activo
            activo = config_dict.get("activo", "false").lower() in ("true", "1", "yes", "on")
            if not activo:
                logger.debug("AI no está activo, usando respuestas básicas")
                return None

            # Validar configuración (puede lanzar HTTPException)
            try:
                _validar_configuracion_ai(config_dict)
            except Exception as e:
                logger.warning(f"Configuración AI inválida: {e}")
                return None

            # Inicializar servicio AI
            ai_service = AIChatService(db=self.db)
            ai_service.inicializar_configuracion()

            # Construir pregunta con contexto del cliente
            pregunta_con_contexto = (
                f"Cliente: {cliente.nombres} {cliente.apellidos or ''}, Cédula: {cliente.cedula}. Pregunta: {pregunta}"
            )

            # Procesar pregunta con AI
            resultado = await ai_service.procesar_pregunta(pregunta_con_contexto)

            if resultado.get("success") and resultado.get("respuesta"):
                logger.info(f"✅ Respuesta AI generada para cliente {cliente.id}")
                return resultado["respuesta"]
            else:
                logger.warning(f"AI no generó respuesta válida: {resultado.get('error', 'Unknown error')}")
                return None

        except Exception as e:
            logger.warning(f"Error consultando Chat AI: {e}")
            return None

    async def _enviar_respuesta(self, to_number: str, mensaje: str, conversacion_id: int) -> Dict[str, any]:
        """
        Enviar respuesta al cliente

        Args:
            to_number: Número de destino
            mensaje: Mensaje a enviar
            conversacion_id: ID de la conversación original

        Returns:
            Resultado del envío
        """
        try:
            resultado = await self.whatsapp_service.send_message(
                to_number=to_number,
                message=mensaje,
            )

            # Guardar respuesta enviada en BD
            if resultado.get("success"):
                respuesta_conversacion = ConversacionWhatsApp(
                    from_number=self.whatsapp_service.phone_number_id,
                    to_number=to_number,
                    message_type="text",
                    body=mensaje,
                    timestamp=datetime.utcnow(),
                    direccion="OUTBOUND",
                    respuesta_id=conversacion_id,
                    procesado=True,
                    respuesta_enviada=True,
                    respuesta_meta_id=resultado.get("message_id"),
                )
                self.db.add(respuesta_conversacion)
                self.db.commit()

            return resultado

        except Exception as e:
            logger.error(f"Error enviando respuesta: {e}", exc_info=True)
            return {"success": False, "message": str(e)}
