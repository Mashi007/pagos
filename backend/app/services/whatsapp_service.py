# backend/app/services/whatsapp_service.py
"""
Servicio para envío de mensajes WhatsApp usando Twilio.
"""
from twilio.rest import Client
from typing import Optional
from datetime import datetime
import logging

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.notificacion import Notificacion, EstadoNotificacion

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Servicio para gestión de WhatsApp"""
    
    def __init__(self):
        # Configuración de Twilio
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.from_number = settings.TWILIO_WHATSAPP_NUMBER
        
        # Inicializar cliente de Twilio
        if self.account_sid and self.auth_token:
            self.client = Client(self.account_sid, self.auth_token)
        else:
            self.client = None
            logger.warning("Credenciales de Twilio no configuradas")
    
    async def send_message(
        self,
        to_number: str,
        message: str,
        notificacion_id: Optional[int] = None
    ) -> bool:
        """
        Enviar mensaje de WhatsApp.
        
        Args:
            to_number: Número de teléfono (formato: +593999999999)
            message: Mensaje a enviar
            notificacion_id: ID de notificación para actualizar estado
        
        Returns:
            True si se envió exitosamente
        """
        if not self.client:
            logger.error("Cliente de Twilio no inicializado")
            return False
        
        try:
            # Formatear número para WhatsApp (debe incluir whatsapp:)
            whatsapp_to = f"whatsapp:{to_number}"
            whatsapp_from = f"whatsapp:{self.from_number}"
            
            # Enviar mensaje
            message_obj = self.client.messages.create(
                body=message,
                from_=whatsapp_from,
                to=whatsapp_to
            )
            
            logger.info(f"WhatsApp enviado a {to_number}. SID: {message_obj.sid}")
            
            # Actualizar notificación
            if notificacion_id:
                self._actualizar_notificacion(
                    notificacion_id,
                    EstadoNotificacion.ENVIADA.value,
                    sid=message_obj.sid
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Error enviando WhatsApp a {to_number}: {str(e)}")
            
            # Actualizar notificación como fallida
            if notificacion_id:
                self._actualizar_notificacion(
                    notificacion_id,
                    EstadoNotificacion.FALLIDA.value,
                    error=str(e)
                )
            
            return False
    
    async def send_template_message(
        self,
        to_number: str,
        template_name: str,
        variables: dict,
        notificacion_id: Optional[int] = None
    ) -> bool:
        """
        Enviar mensaje usando template predefinido.
        
        Args:
            to_number: Número destinatario
            template_name: Nombre del template
            variables: Variables para el template
            notificacion_id: ID de notificación
        
        Returns:
            True si se envió exitosamente
        """
        try:
            # Generar mensaje desde template
            message = self._generate_message_from_template(template_name, variables)
            
            return await self.send_message(
                to_number=to_number,
                message=message,
                notificacion_id=notificacion_id
            )
            
        except Exception as e:
            logger.error(f"Error enviando template WhatsApp: {str(e)}")
            return False
    
    def _generate_message_from_template(self, template_name: str, variables: dict) -> str:
        """
        Generar mensaje desde template.
        """
        templates = {
            "recordatorio_pago": """
🔔 *Recordatorio de Pago*

Hola {cliente_nombre},

Te recordamos que tienes una cuota próxima a vencer:

💰 Monto: ${monto}
📅 Vencimiento: {fecha_vencimiento}
⏰ Días restantes: {dias_restantes}

Por favor, realiza tu pago a tiempo para evitar recargos.

Gracias por tu preferencia.
            """,
            
            "prestamo_aprobado": """
✅ *¡Préstamo Aprobado!*

Hola {cliente_nombre},

¡Buenas noticias! Tu préstamo ha sido APROBADO.

💰 Monto: ${monto}
📅 Plazo: {plazo} meses
💵 Cuota mensual: ${cuota}

Acércate a nuestras oficinas para firmar el contrato.
            """,
            
            "mora": """
⚠️ *Aviso de Mora*

Hola {cliente_nombre},

Tu cuenta presenta mora en el pago:

⏰ Días de mora: {dias_mora}
💰 Saldo pendiente: ${saldo_pendiente}
📌 Recargo: ${recargo_mora}

Por favor, regulariza tu situación para evitar acciones legales.

Contáctanos: {telefono}
            """,
            
            "confirmacion_pago": """
✅ *Pago Recibido*

Hola {cliente_nombre},

Confirmamos la recepción de tu pago:

💰 Monto: ${monto}
📅 Fecha: {fecha}
🔢 Recibo: {recibo}

Gracias por tu puntualidad.
            """,
            
            "cuota_vencida": """
⚠️ *Cuota Vencida*

Hola {cliente_nombre},

Tu cuota del {fecha_vencimiento} está vencida.

💰 Monto: ${monto}
⏰ Días vencidos: {dias_vencidos}

Por favor, regulariza tu pago lo antes posible.
            """
        }
        
        if template_name not in templates:
            raise ValueError(f"Template '{template_name}' no encontrado")
        
        return templates[template_name].format(**variables)
    
    def get_message_status(self, message_sid: str) -> dict:
        """
        Obtener estado de un mensaje enviado.
        
        Args:
            message_sid: SID del mensaje de Twilio
        
        Returns:
            Dict con información del mensaje
        """
        if not self.client:
            return {"error": "Cliente no inicializado"}
        
        try:
            message = self.client.messages(message_sid).fetch()
            
            return {
                "sid": message.sid,
                "status": message.status,
                "to": message.to,
                "from": message.from_,
                "date_sent": message.date_sent,
                "error_code": message.error_code,
                "error_message": message.error_message
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estado del mensaje {message_sid}: {str(e)}")
            return {"error": str(e)}
    
    def _actualizar_notificacion(
        self,
        notificacion_id: int,
        estado: str,
        sid: Optional[str] = None,
        error: Optional[str] = None
    ):
        """
        Actualizar estado de notificación en base de datos.
        """
        try:
            db = SessionLocal()
            notificacion = db.query(Notificacion).filter(
                Notificacion.id == notificacion_id
            ).first()
            
            if notificacion:
                notificacion.estado = estado
                notificacion.enviada_en = datetime.now()
                
                if sid:
                    # Guardar SID de Twilio en metadata
                    if not notificacion.meta_info:
                        notificacion.meta_info = {}
                    notificacion.meta_info['twilio_sid'] = sid
                
                if error:
                    notificacion.error = error
                
                db.commit()
                
        except Exception as e:
            logger.error(f"Error actualizando notificación {notificacion_id}: {str(e)}")
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
        import re
        
        # Formato esperado: +593999999999 (Ecuador)
        pattern = r'^\+\d{10,15}$'
        return bool(re.match(pattern, phone_number))
