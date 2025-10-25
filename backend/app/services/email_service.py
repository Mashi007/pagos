# backend/app/services/email_service.py
"""
Servicio para envío de emails.
Soporta templates HTML y envío asíncrono.
"""

import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

import aiosmtplib
from jinja2 import Template

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.notificacion import EstadoNotificacion, Notificacion

logger = logging.getLogger(__name__)


class EmailService:
    """Servicio para gestión de emails"""

    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.FROM_EMAIL
        self.from_name = settings.FROM_NAME
        self.use_tls = getattr(settings, "SMTP_USE_TLS", True)
        self.use_ssl = getattr(settings, "SMTP_USE_SSL", False)

        # Verificar configuración
        if not self.smtp_user or not self.smtp_password:
            logger.warning("Credenciales de email no configuradas")
            logger.info("Variables requeridas: SMTP_USER, SMTP_PASSWORD")

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html: bool = False,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        notificacion_id: Optional[int] = None,
    ) -> bool:
        """
        Enviar email.

        Args:
            to_email: Email destinatario
            subject: Asunto
            body: Cuerpo del mensaje
            html: Si el body es HTML
            cc: Lista de emails en copia
            bcc: Lista de emails en copia oculta
            notificacion_id: ID de notificación para actualizar estado

        Returns:
            True si se envió exitosamente
        """
        try:
            # Crear mensaje
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email

            if cc:
                message["Cc"] = ", ".join(cc)
            if bcc:
                message["Bcc"] = ", ".join(bcc)

            # Adjuntar contenido
            if html:
                message.attach(MIMEText(body, "html"))
            else:
                message.attach(MIMEText(body, "plain"))

            # Enviar
            async with aiosmtplib.SMTP(
                hostname=self.smtp_host, port=self.smtp_port, use_tls=True
            ) as smtp:
                await smtp.login(self.smtp_user, self.smtp_password)
                await smtp.send_message(message)

            logger.info(f"Email enviado exitosamente a {to_email}")

            # Actualizar notificación
            if notificacion_id:
                self._actualizar_notificacion(
                    notificacion_id, EstadoNotificacion.ENVIADA.value
                )

            return True

        except Exception as e:
            logger.error(f"Error enviando email a {to_email}: {str(e)}")

            # Actualizar notificación como fallida
            if notificacion_id:
                self._actualizar_notificacion(
                    notificacion_id, EstadoNotificacion.FALLIDA.value, error=str(e)
                )

            return False

    async def send_template_email(
        self,
        to_email: str,
        subject: str,
        template_name: str,
        context: dict,
        notificacion_id: Optional[int] = None,
    ) -> bool:
        """
        Enviar email usando template HTML.

        Args:
            to_email: Email destinatario
            subject: Asunto
            template_name: Nombre del template
            context: Variables para el template
            notificacion_id: ID de notificación

        Returns:
            True si se envió exitosamente
        """
        try:
            # Cargar template
            template = self._load_template(template_name)
            html_body = template.render(**context)

            return await self.send_email(
                to_email=to_email,
                subject=subject,
                body=html_body,
                html=True,
                notificacion_id=notificacion_id,
            )

        except Exception as e:
            logger.error(f"Error enviando template email: {str(e)}")
            return False

    def _load_template(self, template_name: str) -> Template:
        """
        Cargar template HTML desde archivo.
        """
        templates = {
            "recordatorio_pago": """
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body { font-family: Arial, sans-serif; }
                        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                        .header { background: #007bff; color: white; padding: 20px; text-align: center; }
                        .content { padding: 20px; background: #f8f9fa; }
                        .footer { text-align: center; padding: 10px; color: #666; font-size: 12px; }
                        .button { background: #28a745; color: white; padding: 10px 20px;
                                  text-decoration: none; border-radius: 5px; display: inline-block; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h2>{{ empresa }}</h2>
                        </div>
                        <div class="content">
                            <p>Estimado/a <strong>{{ cliente_nombre }}</strong>,</p>
                            <p>Le recordamos que tiene una cuota próxima a vencer:</p>
                            <ul>
                                <li>Monto: ${{ monto }}</li>
                                <li>Fecha de vencimiento: {{ fecha_vencimiento }}</li>
                                <li>Días restantes: {{ dias_restantes }}</li>
                            </ul>
                            <p>Por favor, realice su pago a tiempo para evitar recargos.</p>
                            <p style="text-align: center;">
                                <a href="{{ link_pago }}" class="button">Pagar Ahora</a>
                            </p>
                        </div>
                        <div class="footer">
                            <p>{{ empresa }} - {{ telefono }} - {{ email }}</p>
                        </div>
                    </div>
                </body>
                </html>
            """,
            "prestamo_aprobado": """
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body { font-family: Arial, sans-serif; }
                        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                        .header { background: #28a745; color: white; padding: 20px; text-align: center; }
                        .content { padding: 20px; background: #f8f9fa; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h2>¡Préstamo Aprobado!</h2>
                        </div>
                        <div class="content">
                            <p>Estimado/a <strong>{{ cliente_nombre }}</strong>,</p>
                            <p>Nos complace informarle que su solicitud de préstamo ha sido <strong>APROBADA</strong>.</p>
                            <h3>Detalles del Préstamo:</h3>
                            <ul>
                                <li>Monto aprobado: ${{ monto }}</li>
                                <li>Plazo: {{ plazo }} meses</li>
                                <li>Cuota mensual: ${{ cuota }}</li>
                                <li>Tasa de interés: {{ tasa }}%</li>
                            </ul>
                            <p>Por favor, acérquese a nuestras oficinas para firmar el contrato.</p>
                        </div>
                    </div>
                </body>
                </html>
            """,
            "mora": """
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body { font-family: Arial, sans-serif; }
                        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                        .header { background: #dc3545; color: white; padding: 20px; text-align: center; }
                        .content { padding: 20px; background: #f8f9fa; }
                        .warning { background: #fff3cd; border: 1px solid #ffc107;
                                   padding: 15px; margin: 15px 0; border-radius: 5px; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h2>Aviso de Mora</h2>
                        </div>
                        <div class="content">
                            <p>Estimado/a <strong>{{ cliente_nombre }}</strong>,</p>
                            <div class="warning">
                                <p><strong>Su cuenta presenta mora en el pago.</strong></p>
                            </div>
                            <p>Detalles:</p>
                            <ul>
                                <li>Días de mora: {{ dias_mora }}</li>
                                <li>Saldo pendiente: ${{ saldo_pendiente }}</li>
                                <li>Recargo por mora: ${{ recargo_mora }}</li>
                            </ul>
                            <p>Por favor, regularice su situación a la brevedad para evitar acciones legales.</p>
                        </div>
                    </div>
                </body>
                </html>
            """,
        }

        if template_name not in templates:
            raise ValueError(f"Template '{template_name}' no encontrado")

        return Template(templates[template_name])

    def _actualizar_notificacion(
        self, notificacion_id: int, estado: str, error: Optional[str] = None
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

                if error:
                    notificacion.error = error

                db.commit()

        except Exception as e:
            logger.error(f"Error actualizando notificación {notificacion_id}: {str(e)}")
        finally:
            db.close()
