"""
Servicio de email
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Servicio para envío de emails con soporte para envíos masivos"""

    def __init__(self, db: Optional[Session] = None, reuse_connection: bool = False):
        """
        Inicializar servicio de email

        Args:
            db: Sesión de base de datos opcional para leer configuración desde BD
            reuse_connection: Si True, reutiliza la conexión SMTP para múltiples envíos (útil para envíos masivos)
        """
        self.db = db
        self.reuse_connection = reuse_connection
        self._smtp_server_connection = None
        self._cargar_configuracion()

    def _cargar_configuracion(self):
        """Cargar configuración desde BD si está disponible, sino usar settings por defecto"""
        # Valores por defecto desde settings
        self.smtp_server = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.FROM_EMAIL
        self.from_name = settings.FROM_NAME
        self.smtp_use_tls = settings.SMTP_USE_TLS
        self.modo_pruebas = False
        self.email_pruebas = ""

        # Si hay sesión de BD, intentar cargar configuración desde BD
        if self.db:
            try:
                from app.models.configuracion_sistema import ConfiguracionSistema

                configs = self.db.query(ConfiguracionSistema).filter(ConfiguracionSistema.categoria == "EMAIL").all()

                if configs:
                    config_dict = {config.clave: config.valor for config in configs}

                    # Actualizar valores si existen en BD
                    if config_dict.get("smtp_host"):
                        self.smtp_server = config_dict["smtp_host"]
                    if config_dict.get("smtp_port"):
                        try:
                            self.smtp_port = int(config_dict["smtp_port"])
                        except (ValueError, TypeError):
                            logger.warning(f"Puerto SMTP inválido en BD: {config_dict.get('smtp_port')}")
                    if config_dict.get("smtp_user"):
                        self.smtp_username = config_dict["smtp_user"]
                    if config_dict.get("smtp_password"):
                        self.smtp_password = config_dict["smtp_password"]
                    if config_dict.get("from_email"):
                        self.from_email = config_dict["from_email"]
                    if config_dict.get("from_name"):
                        self.from_name = config_dict["from_name"]
                    if config_dict.get("smtp_use_tls"):
                        self.smtp_use_tls = config_dict["smtp_use_tls"].lower() in ("true", "1", "yes", "on")
                    if config_dict.get("modo_pruebas"):
                        self.modo_pruebas = config_dict["modo_pruebas"].lower() in ("true", "1", "yes", "on")
                    if config_dict.get("email_pruebas"):
                        self.email_pruebas = config_dict["email_pruebas"]

                    logger.info("✅ Configuración de email cargada desde base de datos")
                    if self.modo_pruebas:
                        logger.warning(f"⚠️ MODO PRUEBAS ACTIVO: Todos los emails se enviarán a {self.email_pruebas}")
                    return

            except Exception as e:
                logger.warning(f"⚠️ No se pudo cargar configuración de email desde BD: {str(e)}. Usando valores por defecto.")

        logger.debug("📧 Usando configuración de email por defecto desde settings")

    def send_email(self, to_emails: List[str], subject: str, body: str, is_html: bool = False, bcc_emails: Optional[List[str]] = None) -> Dict[str, Any]:
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
            # Recargar configuración para obtener modo_pruebas actualizado
            self._cargar_configuracion()
            
            # Si está en modo pruebas, redirigir todos los emails a email_pruebas
            emails_destinatarios = to_emails.copy()
            if self.modo_pruebas and self.email_pruebas:
                emails_originales = ", ".join(to_emails)
                # Agregar información de destinatarios originales al asunto y cuerpo
                subject = f"[PRUEBAS - Originalmente para: {emails_originales}] {subject}"
                body = f"""
                <div style="background-color: #fff3cd; border: 2px solid #ffc107; padding: 10px; margin-bottom: 20px;">
                    <strong>⚠️ MODO PRUEBAS ACTIVO</strong><br>
                    Este email estaba destinado a: {emails_originales}<br>
                    En producción, este email se enviaría a los destinatarios reales.
                </div>
                {body}
                """
                emails_destinatarios = [self.email_pruebas]
                logger.warning(f"🧪 MODO PRUEBAS: Redirigiendo email de {', '.join(to_emails)} a {self.email_pruebas}")
            
            # Crear mensaje
            msg = MIMEMultipart()
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = ", ".join(emails_destinatarios)
            msg["Subject"] = subject

            # Agregar CCO (BCC) si se proporciona
            emails_cco = []
            if bcc_emails:
                # Filtrar emails vacíos y validar
                emails_cco = [email.strip() for email in bcc_emails if email and email.strip()]
                if emails_cco:
                    msg["Bcc"] = ", ".join(emails_cco)
                    logger.info(f"📧 Agregando {len(emails_cco)} correo(s) en CCO: {', '.join(emails_cco)}")

            # Agregar cuerpo
            if is_html:
                msg.attach(MIMEText(body, "html"))
            else:
                msg.attach(MIMEText(body, "plain"))

            # Enviar email - reutilizar conexión si está habilitado
            if self.reuse_connection and self._smtp_server_connection:
                # Reutilizar conexión existente
                server = self._smtp_server_connection
                try:
                    # Verificar que la conexión sigue activa
                    server.noop()
                except (smtplib.SMTPServerDisconnected, OSError):
                    # Reconectar si se perdió la conexión
                    logger.warning("⚠️ Conexión SMTP perdida, reconectando...")
                    self._smtp_server_connection = None
                    server = None
            else:
                server = None

            if not server:
                # Crear nueva conexión
                server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30)

                if self.smtp_use_tls:
                    server.starttls()

                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)

                # Guardar conexión si se debe reutilizar
                if self.reuse_connection:
                    self._smtp_server_connection = server

            text = msg.as_string()
            # Incluir CCO en la lista de destinatarios para sendmail
            todos_destinatarios = emails_destinatarios + emails_cco
            server.sendmail(self.from_email, todos_destinatarios, text)
            
            # Solo cerrar conexión si no se reutiliza
            if not self.reuse_connection:
                server.quit()

            mensaje_exito = "Email enviado exitosamente"
            if self.modo_pruebas:
                mensaje_exito = f"Email enviado exitosamente (MODO PRUEBAS: originalmente para {', '.join(to_emails)})"
            if emails_cco:
                mensaje_exito += f" (CCO: {', '.join(emails_cco)})"

            logger.info(f"Email enviado exitosamente a: {', '.join(emails_destinatarios)}" + (f" (CCO: {', '.join(emails_cco)})" if emails_cco else ""))
            return {
                "success": True,
                "message": mensaje_exito,
                "recipients": emails_destinatarios,
                "bcc_recipients": emails_cco if emails_cco else [],
                "original_recipients": to_emails if self.modo_pruebas else None,
                "modo_pruebas": self.modo_pruebas,
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

    def close_connection(self):
        """Cerrar conexión SMTP reutilizada si existe"""
        if self._smtp_server_connection:
            try:
                self._smtp_server_connection.quit()
            except Exception as e:
                logger.warning(f"⚠️ Error cerrando conexión SMTP: {e}")
            finally:
                self._smtp_server_connection = None

    def test_connection(self) -> Dict[str, Any]:
        """
        Probar conexión SMTP

        Returns:
            Dict con resultado de la prueba
        """
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)

            if self.smtp_use_tls:
                server.starttls()

            if self.smtp_username and self.smtp_password:
                server.login(self.smtp_username, self.smtp_password)

            server.quit()

            return {"success": True, "message": "Conexión SMTP exitosa"}

        except Exception as e:
            logger.error(f"Error probando conexión SMTP: {str(e)}")
            return {"success": False, "message": f"Error de conexión SMTP: {str(e)}"}
