"""
Servicio de email
"""

import logging
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, Tuple

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
        self.modo_pruebas = True  # Por defecto: Pruebas (más seguro, evita envíos accidentales)
        self.email_pruebas = ""
        self.email_activo = True  # ✅ Por defecto: activo

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
                    # ✅ Cargar estado activo/inactivo
                    if config_dict.get("email_activo"):
                        self.email_activo = config_dict["email_activo"].lower() in ("true", "1", "yes", "on")
                    else:
                        # Si no existe, por defecto está activo
                        self.email_activo = True

                    logger.info("✅ Configuración de email cargada desde base de datos")
                    if self.modo_pruebas:
                        if self.email_pruebas:
                            logger.warning(f"⚠️ MODO PRUEBAS ACTIVO: Todos los emails se enviarán a {self.email_pruebas}")
                        else:
                            logger.warning(
                                "⚠️ MODO PRUEBAS ACTIVO pero email_pruebas no está configurado. Los emails fallarán si se intentan enviar."
                            )
                    return

            except Exception as e:
                logger.warning(f"⚠️ No se pudo cargar configuración de email desde BD: {str(e)}. Usando valores por defecto.")

        logger.debug("📧 Usando configuración de email por defecto desde settings")

    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        body: str,
        is_html: bool = False,
        bcc_emails: Optional[List[str]] = None,
        forzar_envio_real: bool = False,
    ) -> Dict[str, Any]:
        """
        Enviar email

        Args:
            to_emails: Lista de emails destinatarios
            subject: Asunto del email
            body: Cuerpo del email
            is_html: Si el cuerpo es HTML
            bcc_emails: Lista opcional de emails en CCO (BCC)
            forzar_envio_real: Si True, ignora modo_pruebas y envía al destinatario real.
                              Útil para pruebas de configuración en modo Producción.

        Returns:
            Dict con resultado del envío
        """
        try:
            # Recargar configuración para obtener modo_pruebas y email_activo actualizado
            self._cargar_configuracion()

            # ✅ Verificar si el email está activado
            if not self.email_activo:
                logger.info("📧 Email desactivado - No se enviará el email (proceso no interrumpido)")
                return {
                    "success": False,
                    "message": "⚠️ El envío de emails está desactivado. Activa el servicio en Configuración de Email.",
                    "error_type": "EMAIL_DISABLED",
                    "recipients": to_emails,
                    "email_activo": False,
                }

            # Validar configuración antes de enviar
            if not self.smtp_server:
                raise ValueError("SMTP server no configurado")
            if not self.smtp_port or self.smtp_port <= 0:
                raise ValueError(f"Puerto SMTP inválido: {self.smtp_port}")
            if not self.from_email:
                raise ValueError("Email remitente (from_email) no configurado")

            # Si está en modo pruebas, redirigir todos los emails a email_pruebas
            # (excepto si se fuerza envío real, útil para pruebas de configuración)
            emails_destinatarios = to_emails.copy()
            if self.modo_pruebas and not forzar_envio_real:
                if not self.email_pruebas:
                    raise ValueError(
                        "⚠️ MODO PRUEBAS activo pero email_pruebas no está configurado. "
                        "Configure un email de pruebas o desactive modo_pruebas para enviar a destinatarios reales."
                    )
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
            from datetime import datetime
            from email.utils import formatdate, make_msgid, formataddr
            import uuid
            import html as html_module

            msg = MIMEMultipart("alternative")  # ✅ multipart/alternative para HTML + texto plano

            # ✅ Mejorar formato del From (RFC-compliant)
            if self.from_name and self.from_name.strip():
                msg["From"] = formataddr((self.from_name, self.from_email))
            else:
                msg["From"] = self.from_email

            msg["To"] = ", ".join(emails_destinatarios)
            msg["Subject"] = subject
            msg["Date"] = formatdate(localtime=True)

            # ✅ Message-ID único y RFC-compliant
            domain = self.from_email.split("@")[1] if "@" in self.from_email else "rapicredit.com"
            unique_id = str(uuid.uuid4()).replace("-", "")
            msg["Message-ID"] = f"<{unique_id}@{domain}>"

            # ✅ Headers estándar para mejor deliverability
            msg["Reply-To"] = self.from_email
            msg["Return-Path"] = self.from_email  # Para bounces
            msg["MIME-Version"] = "1.0"

            # ✅ Headers para evitar spam
            msg["X-Mailer"] = "RapiCredit Email System v1.0"
            msg["X-Priority"] = "3"  # Prioridad normal (1=alta, 3=normal, 5=baja)
            msg["Precedence"] = "bulk"  # Para emails transaccionales/notificaciones
            msg["Auto-Submitted"] = "auto-generated"  # Indica email automático del sistema

            # ✅ Headers de identificación (mejora reputación)
            msg["X-Entity-Ref-ID"] = unique_id  # ID único para tracking
            msg["X-Source"] = "RapiCredit-System"
            msg["X-Source-Domain"] = domain

            # Agregar CCO (BCC) si se proporciona
            emails_cco = []
            if bcc_emails:
                # Filtrar emails vacíos y validar
                emails_cco = [email.strip() for email in bcc_emails if email and email.strip()]
                if emails_cco:
                    msg["Bcc"] = ", ".join(emails_cco)
                    logger.info(f"📧 Agregando {len(emails_cco)} correo(s) en CCO: {', '.join(emails_cco)}")

            # ✅ Agregar versión de texto plano Y HTML para mejor deliverability
            # Los filtros spam prefieren emails con ambas versiones
            if is_html:
                # Extraer texto plano del HTML (mejorado para mejor formato)
                import re
                import html as html_module

                # Decodificar entidades HTML (&nbsp;, &amp;, etc.)
                texto_plano = html_module.unescape(body)
                # Remover tags HTML
                texto_plano = re.sub(r"<[^>]+>", "", texto_plano)
                # Remover múltiples espacios y saltos de línea
                texto_plano = re.sub(r"\s+", " ", texto_plano)
                # Remover espacios al inicio y final
                texto_plano = texto_plano.strip()
                # Reemplazar saltos de línea múltiples por uno solo
                texto_plano = re.sub(r"\n\s*\n", "\n\n", texto_plano)

                # Si el texto plano está vacío, usar un mensaje por defecto
                if not texto_plano or len(texto_plano.strip()) < 10:
                    texto_plano = "Este es un email HTML. Si no puedes ver el contenido, por favor abre este email en un cliente de correo que soporte HTML."

                # ✅ Agregar texto plano primero (los clientes de email lo prefieren)
                # Especificar charset explícitamente
                texto_plano_part = MIMEText(texto_plano, "plain", "utf-8")
                texto_plano_part.set_charset("utf-8")
                msg.attach(texto_plano_part)

                # ✅ Agregar HTML con charset explícito
                html_part = MIMEText(body, "html", "utf-8")
                html_part.set_charset("utf-8")
                msg.attach(html_part)
            else:
                # ✅ Texto plano con charset explícito
                texto_part = MIMEText(body, "plain", "utf-8")
                texto_part.set_charset("utf-8")
                msg.attach(texto_part)

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
                # ✅ Puerto 465 requiere SSL (SMTP_SSL), puerto 587 requiere TLS (SMTP + starttls)
                if self.smtp_port == 465:
                    # Puerto 465: Usar SSL directamente (no TLS)
                    server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=30)
                    logger.debug("✅ Conexión SSL establecida para puerto 465")
                else:
                    # Puerto 587 u otros: Usar SMTP normal con TLS opcional
                    server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30)
                    if self.smtp_use_tls:
                        server.starttls()
                        logger.debug("✅ TLS iniciado correctamente")

                # Validar credenciales antes de intentar login
                if self.smtp_username and self.smtp_password:
                    if not self.smtp_username.strip() or not self.smtp_password.strip():
                        raise ValueError("Credenciales SMTP (usuario o contraseña) están vacías")
                    server.login(self.smtp_username, self.smtp_password)
                elif self.smtp_username or self.smtp_password:
                    # Si solo uno de los dos está configurado, es un error
                    raise ValueError("Credenciales SMTP incompletas: se requiere tanto usuario como contraseña")

                # Guardar conexión si se debe reutilizar
                if self.reuse_connection:
                    self._smtp_server_connection = server

            # ✅ Asegurar que el mensaje esté correctamente formateado
            # Usar as_string() con policy para mejor compatibilidad
            try:
                text = msg.as_string()
            except Exception as e:
                logger.warning(f"⚠️ Error formateando mensaje, usando método alternativo: {e}")
                # Método alternativo si as_string() falla
                from email import policy

                text = msg.as_string(policy=policy.SMTP)

            # Incluir CCO en la lista de destinatarios para sendmail
            todos_destinatarios = emails_destinatarios + emails_cco

            # ✅ Logging detallado antes de enviar
            logger.info(
                f"📧 Enviando email - "
                f"De: {self.from_email}, "
                f"Para: {', '.join(emails_destinatarios)}, "
                f"Modo Pruebas: {self.modo_pruebas}, "
                f"Forzar Envío Real: {forzar_envio_real}, "
                f"Destinatarios originales: {', '.join(to_emails) if self.modo_pruebas else 'N/A'}, "
                f"Message-ID: {msg['Message-ID']}"
            )

            # ✅ Enviar usando sendmail con parámetros explícitos
            # Esto asegura mejor manejo de errores y mejor deliverability
            server.sendmail(self.from_email, todos_destinatarios, text)  # from_addr  # to_addrs  # msg

            # Solo cerrar conexión si no se reutiliza
            if not self.reuse_connection:
                server.quit()

            mensaje_exito = "Email enviado exitosamente"
            if self.modo_pruebas and not forzar_envio_real:
                mensaje_exito = f"Email enviado exitosamente (MODO PRUEBAS: originalmente para {', '.join(to_emails)})"
            if emails_cco:
                mensaje_exito += f" (CCO: {', '.join(emails_cco)})"

            logger.info(
                f"✅ Email enviado exitosamente a: {', '.join(emails_destinatarios)}"
                + (f" (CCO: {', '.join(emails_cco)})" if emails_cco else "")
                + (f" | Originalmente para: {', '.join(to_emails)}" if self.modo_pruebas and not forzar_envio_real else "")
            )
            return {
                "success": True,
                "message": mensaje_exito,
                "recipients": emails_destinatarios,
                "bcc_recipients": emails_cco if emails_cco else [],
                "original_recipients": to_emails if self.modo_pruebas else None,
                "modo_pruebas": self.modo_pruebas,
            }

        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"Error de autenticación SMTP: {str(e)}. Verifique usuario y contraseña."
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "error_type": "AUTHENTICATION_ERROR",
                "recipients": to_emails,
            }
        except smtplib.SMTPConnectError as e:
            error_msg = f"Error conectando al servidor SMTP {self.smtp_server}:{self.smtp_port}: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "error_type": "CONNECTION_ERROR",
                "recipients": to_emails,
            }
        except smtplib.SMTPServerDisconnected as e:
            error_msg = f"Conexión SMTP perdida: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "error_type": "DISCONNECTED_ERROR",
                "recipients": to_emails,
            }
        except smtplib.SMTPException as e:
            error_msg = f"Error SMTP: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "error_type": "SMTP_ERROR",
                "recipients": to_emails,
            }
        except ValueError as e:
            # Errores de validación de configuración
            error_msg = f"Error de configuración: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "error_type": "CONFIGURATION_ERROR",
                "recipients": to_emails,
            }
        except Exception as e:
            error_msg = f"Error inesperado enviando email: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "message": error_msg,
                "error_type": "UNKNOWN_ERROR",
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

    def send_bulk_emails(
        self,
        emails_data: List[Dict[str, Any]],
        subject: str,
        body_template: str,
        is_html: bool = False,
        batch_size: int = 10,
        delay_between_emails: float = 1.0,
        delay_between_batches: float = 5.0,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ) -> Dict[str, Any]:
        """
        ✅ Algoritmo optimizado para envíos masivos de emails

        Características:
        - Rate limiting para evitar bloqueos de Gmail
        - Batching (enviar en lotes pequeños)
        - Delays entre envíos y lotes
        - Retry con backoff exponencial
        - Manejo de errores individual por email
        - Reutilización de conexión SMTP
        - Logging detallado de progreso

        Args:
            emails_data: Lista de diccionarios con datos de cada email
                        Cada dict debe tener: {'email': str, 'variables': dict (opcional)}
            subject: Asunto del email (puede contener variables {nombre}, {email}, etc.)
            body_template: Plantilla del cuerpo (puede contener variables)
            is_html: Si el cuerpo es HTML
            batch_size: Tamaño de cada lote (default: 10 emails por lote)
            delay_between_emails: Segundos de espera entre cada email (default: 1.0)
            delay_between_batches: Segundos de espera entre lotes (default: 5.0)
            max_retries: Intentos máximos por email si falla (default: 3)
            retry_delay: Segundos base de espera antes de reintentar (default: 2.0)

        Returns:
            Dict con estadísticas de envío:
            {
                'total': int,
                'enviados': int,
                'fallidos': int,
                'errores': List[Dict],
                'tiempo_total': float,
                'emails_por_segundo': float,
                'tasa_exito': float
            }
        """
        start_time = time.time()
        total_emails = len(emails_data)
        enviados = 0
        fallidos = 0
        errores = []

        # ✅ Recargar configuración para verificar email_activo
        self._cargar_configuracion()

        # ✅ Verificar si el email está activado
        if not self.email_activo:
            logger.warning("📧 Email desactivado - No se enviarán emails masivos (proceso no interrumpido)")
            return {
                "total": total_emails,
                "enviados": 0,
                "fallidos": total_emails,
                "errores": [
                    {
                        "email": "all",
                        "error": "El envío de emails está desactivado. Activa el servicio en Configuración de Email.",
                        "intentos": 0,
                    }
                ],
                "tiempo_total": 0,
                "emails_por_segundo": 0,
                "tasa_exito": 0,
            }

        logger.info(f"📧 Iniciando envío masivo de {total_emails} emails")
        logger.info(
            f"⚙️ Configuración: batch_size={batch_size}, delay_emails={delay_between_emails}s, delay_batches={delay_between_batches}s"
        )

        # ✅ Habilitar reutilización de conexión para envíos masivos
        self.reuse_connection = True

        try:
            # Dividir emails en lotes
            batches = [emails_data[i : i + batch_size] for i in range(0, total_emails, batch_size)]
            total_batches = len(batches)

            logger.info(f"📦 Dividido en {total_batches} lotes de máximo {batch_size} emails cada uno")

            for batch_num, batch in enumerate(batches, 1):
                logger.info(f"📦 Procesando lote {batch_num}/{total_batches} ({len(batch)} emails)")

                for idx, email_data in enumerate(batch, 1):
                    email_destino = email_data.get("email", "")
                    variables = email_data.get("variables", {})

                    if not email_destino:
                        logger.warning(f"⚠️ Email vacío en índice {idx}, saltando...")
                        fallidos += 1
                        errores.append({"email": email_destino or "N/A", "error": "Email vacío", "intentos": 0})
                        continue

                    # Reemplazar variables en subject y body
                    try:
                        subject_final = subject.format(**variables) if variables else subject
                        body_final = body_template.format(**variables) if variables else body_template
                    except KeyError as e:
                        logger.warning(f"⚠️ Variable faltante en email {email_destino}: {e}")
                        subject_final = subject
                        body_final = body_template

                    # ✅ Intentar enviar con retry
                    intento = 0
                    exito = False

                    while intento < max_retries and not exito:
                        intento += 1
                        try:
                            resultado = self.send_email(
                                to_emails=[email_destino],
                                subject=subject_final,
                                body=body_final,
                                is_html=is_html,
                                forzar_envio_real=True,  # En envíos masivos, siempre enviar real
                            )

                            if resultado.get("success"):
                                enviados += 1
                                exito = True
                                if intento > 1:
                                    logger.info(f"✅ Email {email_destino} enviado en intento {intento}")
                            else:
                                raise Exception(resultado.get("message", "Error desconocido"))

                        except smtplib.SMTPRecipientsRefused as e:
                            # Email rechazado por el servidor (email inválido)
                            logger.warning(f"⚠️ Email rechazado: {email_destino} - {str(e)}")
                            fallidos += 1
                            errores.append(
                                {"email": email_destino, "error": f"Email rechazado: {str(e)}", "intentos": intento}
                            )
                            exito = True  # No reintentar emails inválidos

                        except smtplib.SMTPDataError as e:
                            # Error de datos (posible rate limit)
                            error_msg = str(e).lower()
                            if "rate limit" in error_msg or "too many" in error_msg or "550" in str(e):
                                wait_time = retry_delay * (2**intento)  # Backoff exponencial
                                logger.warning(f"⚠️ Rate limit detectado, esperando {wait_time}s...")
                                if intento < max_retries:
                                    time.sleep(wait_time)
                                    continue  # Reintentar
                            fallidos += 1
                            errores.append({"email": email_destino, "error": f"Error SMTP: {str(e)}", "intentos": intento})
                            exito = True

                        except (smtplib.SMTPException, Exception) as e:
                            # Otros errores SMTP
                            if intento < max_retries:
                                wait_time = retry_delay * (2**intento)  # Backoff exponencial
                                logger.warning(
                                    f"⚠️ Error enviando a {email_destino} (intento {intento}/{max_retries}): {str(e)}"
                                )
                                logger.info(f"⏳ Esperando {wait_time}s antes de reintentar...")
                                time.sleep(wait_time)
                            else:
                                logger.error(f"❌ Falló después de {max_retries} intentos: {email_destino} - {str(e)}")
                                fallidos += 1
                                errores.append(
                                    {
                                        "email": email_destino,
                                        "error": f"Error después de {max_retries} intentos: {str(e)}",
                                        "intentos": intento,
                                    }
                                )
                                exito = True

                    # ✅ Delay entre emails (excepto el último del lote)
                    if idx < len(batch):
                        time.sleep(delay_between_emails)

                # ✅ Delay entre lotes (excepto el último lote)
                if batch_num < total_batches:
                    logger.info(f"⏸️ Pausa de {delay_between_batches}s entre lotes para evitar rate limiting...")
                    time.sleep(delay_between_batches)

        finally:
            # ✅ Cerrar conexión SMTP al finalizar
            self.close_connection()

        tiempo_total = time.time() - start_time
        emails_por_segundo = enviados / tiempo_total if tiempo_total > 0 else 0

        resultado = {
            "total": total_emails,
            "enviados": enviados,
            "fallidos": fallidos,
            "errores": errores,
            "tiempo_total": round(tiempo_total, 2),
            "emails_por_segundo": round(emails_por_segundo, 2),
            "tasa_exito": round((enviados / total_emails * 100) if total_emails > 0 else 0, 2),
        }

        logger.info(f"✅ Envío masivo completado: {enviados}/{total_emails} enviados ({resultado['tasa_exito']}%)")
        logger.info(f"⏱️ Tiempo total: {tiempo_total:.2f}s | Velocidad: {emails_por_segundo:.2f} emails/segundo")

        if fallidos > 0:
            logger.warning(f"⚠️ {fallidos} emails fallaron. Revisa los errores para más detalles.")

        return resultado

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
            # Validar configuración antes de probar
            if not self.smtp_server:
                return {"success": False, "message": "SMTP server no configurado", "error_type": "CONFIGURATION_ERROR"}
            if not self.smtp_port or self.smtp_port <= 0:
                return {
                    "success": False,
                    "message": f"Puerto SMTP inválido: {self.smtp_port}",
                    "error_type": "CONFIGURATION_ERROR",
                }
            if not self.from_email:
                return {
                    "success": False,
                    "message": "Email remitente (from_email) no configurado",
                    "error_type": "CONFIGURATION_ERROR",
                }

            # ✅ Puerto 465 requiere SSL (SMTP_SSL), puerto 587 requiere TLS (SMTP + starttls)
            if self.smtp_port == 465:
                # Puerto 465: Usar SSL directamente (no TLS)
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=30)
                logger.debug("✅ Conexión SSL establecida para puerto 465")
            else:
                # Puerto 587 u otros: Usar SMTP normal con TLS opcional
                server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30)
                if self.smtp_use_tls:
                    server.starttls()
                    logger.debug("✅ TLS iniciado correctamente")

            if self.smtp_username and self.smtp_password:
                if not self.smtp_username.strip() or not self.smtp_password.strip():
                    server.quit()
                    return {"success": False, "message": "Credenciales SMTP vacías", "error_type": "CONFIGURATION_ERROR"}
                server.login(self.smtp_username, self.smtp_password)
            elif self.smtp_username or self.smtp_password:
                server.quit()
                return {"success": False, "message": "Credenciales SMTP incompletas", "error_type": "CONFIGURATION_ERROR"}

            server.quit()

            return {"success": True, "message": "Conexión SMTP exitosa"}

        except smtplib.SMTPAuthenticationError as e:
            error_msg = str(e).lower()
            error_code = str(e)
            # ✅ Detectar mensajes específicos de Gmail/Google Workspace
            # Código 534 o 5.7.9 = Application-specific password required
            if "application-specific password required" in error_msg or "534" in error_code or "5.7.9" in error_code:
                mensaje = "Gmail/Google Workspace requiere una Contraseña de Aplicación (App Password). Activa 2FA y genera una App Password en https://myaccount.google.com/apppasswords"
                logger.warning(f"⚠️ {mensaje}")
            elif "username and password not accepted" in error_msg or "535" in error_code:
                mensaje = "Gmail/Google Workspace rechazó las credenciales. Verifica que uses una App Password (no tu contraseña normal) y que tengas 2FA activado."
                logger.warning(f"⚠️ {mensaje}")
            else:
                mensaje = f"Error de autenticación con Gmail/Google Workspace: {str(e)}"
                logger.warning(f"⚠️ {mensaje}")
            return {"success": False, "message": mensaje, "error_type": "AUTHENTICATION_ERROR", "gmail_error": True}
        except smtplib.SMTPConnectError as e:
            return {
                "success": False,
                "message": f"Error conectando a {self.smtp_server}:{self.smtp_port}: {str(e)}",
                "error_type": "CONNECTION_ERROR",
            }
        except Exception as e:
            logger.error(f"Error probando conexión SMTP: {str(e)}", exc_info=True)
            return {"success": False, "message": f"Error de conexión SMTP: {str(e)}", "error_type": "UNKNOWN_ERROR"}
