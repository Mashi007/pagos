# backend/app/services/email_service.py
"""Servicio de envío de emails

Configuración y envío de emails usando SMTP
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Servicio para envío de emails"""


    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.FROM_EMAIL


    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        body: str,
        is_html: bool = False,
    ) -> Dict[str, any]:
        """
        Enviar email

        Args:
            to_emails: Lista de emails destinatarios
            subject: Asunto del email
            body: Cuerpo del email
            is_html: Si el cuerpo es HTML

        Returns:
            Dict con resultado del envío
        """
        try:
            # Crear mensaje
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = subject

            # Agregar cuerpo
            if is_html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))

            # Enviar email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)

            text = msg.as_string()
            server.sendmail(self.from_email, to_emails, text)
            server.quit()

            logger.info(f"Email enviado exitosamente a {to_emails}")
            return {
                "success": True,
                "message": "Email enviado exitosamente",
                "recipients": to_emails
            }

        except Exception as e:
            logger.error(f"Error enviando email: {e}")
            return {
                "success": False,
                "error": str(e),
                "recipients": to_emails
            }


    def send_notification_email(
        self,
        to_email: str,
        notification_type: str,
        data: Dict[str, any]
    ) -> Dict[str, any]:
        """
        Enviar email de notificación

        Args:
            to_email: Email destinatario
            notification_type: Tipo de notificación
            data: Datos para el template

        Returns:
            Dict con resultado del envío
        """
        try:
            # Generar contenido basado en tipo
            if notification_type == "payment_reminder":
                subject = "Recordatorio de Pago"
                body = f"""
                Estimado/a {data.get('client_name', 'Cliente')},

                Le recordamos que tiene un pago pendiente por el monto de ${data.get('amount', '0')}.
                Fecha de vencimiento: {data.get('due_date', 'N/A')}

                Por favor, realice su pago a la brevedad posible.

                Saludos cordiales,
                Equipo de Financiamiento
                """
            else:
                subject = "Notificación del Sistema"
                body = f"""
                Estimado/a {data.get('client_name', 'Cliente')},

                {data.get('message', 'Tiene una nueva notificación del sistema.')}

                Saludos cordiales,
                Equipo de Financiamiento
                """

            return self.send_email([to_email], subject, body)

        except Exception as e:
            logger.error(f"Error enviando email de notificación: {e}")
            return {
                "success": False,
                "error": str(e)
            }
