"""
Servicio de email
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Servicio para envío de emails"""

    def __init__(self):
        """Inicializar servicio de email"""
        self.smtp_server = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.FROM_EMAIL
        self.from_name = settings.FROM_NAME

    def send_email(self, to_emails: List[str], subject: str, body: str, is_html: bool = False) -> Dict[str, Any]:
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
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = ", ".join(to_emails)
            msg["Subject"] = subject

            # Agregar cuerpo
            if is_html:
                msg.attach(MIMEText(body, "html"))
            else:
                msg.attach(MIMEText(body, "plain"))

            # Enviar email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)

            if settings.SMTP_USE_TLS:
                server.starttls()

            if self.smtp_username and self.smtp_password:
                server.login(self.smtp_username, self.smtp_password)

            text = msg.as_string()
            server.sendmail(self.from_email, to_emails, text)
            server.quit()

            logger.info(f"Email enviado exitosamente a: {', '.join(to_emails)}")
            return {
                "success": True,
                "message": "Email enviado exitosamente",
                "recipients": to_emails,
            }

        except Exception as e:
            logger.error(f"Error enviando email: {str(e)}")
            return {
                "success": False,
                "message": f"Error enviando email: {str(e)}",
                "recipients": to_emails,
            }

    def send_welcome_email(self, email: str, name: str) -> Dict[str, Any]:
        """
        Enviar email de bienvenida

        Args:
            email: Email del usuario
            name: Nombre del usuario

        Returns:
            Dict con resultado del envío
        """
        subject = f"Bienvenido a {settings.APP_NAME}"
        body = f"""
        <html>
        <body>
            <h2>¡Bienvenido {name}!</h2>
            <p>Gracias por registrarte en {settings.APP_NAME}.</p>
            <p>Tu cuenta ha sido creada exitosamente.</p>
            <p>Saludos,<br>El equipo de {settings.APP_NAME}</p>
        </body>
        </html>
        """

        return self.send_email([email], subject, body, is_html=True)

    def send_password_reset_email(self, email: str, reset_token: str, name: str) -> Dict[str, Any]:
        """
        Enviar email de reset de contraseña

        Args:
            email: Email del usuario
            reset_token: Token de reset
            name: Nombre del usuario

        Returns:
            Dict con resultado del envío
        """
        subject = f"Reset de contraseña - {settings.APP_NAME}"
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"

        body = f"""
        <html>
        <body>
            <h2>Reset de contraseña</h2>
            <p>Hola {name},</p>
            <p>Has solicitado un reset de contraseña para tu cuenta en {settings.APP_NAME}.</p>
            <p>Haz clic en el siguiente enlace para restablecer tu contraseña:</p>
            <p><a href="{reset_url}">Restablecer contraseña</a></p>
            <p>Si no solicitaste este reset, puedes ignorar este email.</p>
            <p>Saludos,<br>El equipo de {settings.APP_NAME}</p>
        </body>
        </html>
        """

        return self.send_email([email], subject, body, is_html=True)

    def send_payment_reminder_email(self, email: str, name: str, loan_amount: float, due_date: str) -> Dict[str, Any]:
        """
        Enviar email de recordatorio de pago

        Args:
            email: Email del cliente
            name: Nombre del cliente
            loan_amount: Monto del préstamo
            due_date: Fecha de vencimiento

        Returns:
            Dict con resultado del envío
        """
        subject = f"Recordatorio de pago - {settings.APP_NAME}"

        body = f"""
        <html>
        <body>
            <h2>Recordatorio de pago</h2>
            <p>Hola {name},</p>
            <p>Te recordamos que tienes un pago pendiente:</p>
            <ul>
                <li><strong>Monto:</strong> ${loan_amount:,.2f}</li>
                <li><strong>Fecha de vencimiento:</strong> {due_date}</li>
            </ul>
            <p>Por favor realiza tu pago a tiempo para evitar cargos adicionales.</p>
            <p>Saludos,<br>El equipo de {settings.APP_NAME}</p>
        </body>
        </html>
        """

        return self.send_email([email], subject, body, is_html=True)

    def test_connection(self) -> Dict[str, Any]:
        """
        Probar conexión SMTP

        Returns:
            Dict con resultado de la prueba
        """
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)

            if settings.SMTP_USE_TLS:
                server.starttls()

            if self.smtp_username and self.smtp_password:
                server.login(self.smtp_username, self.smtp_password)

            server.quit()

            return {"success": True, "message": "Conexión SMTP exitosa"}

        except Exception as e:
            logger.error(f"Error probando conexión SMTP: {str(e)}")
            return {"success": False, "message": f"Error de conexión SMTP: {str(e)}"}
