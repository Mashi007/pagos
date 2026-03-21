# -*- coding: utf-8 -*-
"""
Servicio de Email mejorado con reintentos, transacciones y manejo robusto de errores.
"""

import time
import smtplib
from typing import Optional, List, Dict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import logging

logger = logging.getLogger(__name__)


class EmailServiceConReintentos:
    """
    Servicio de email con reintentos automáticos usando exponential backoff.
    """
    
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        max_reintentos: int = 3,
        delay_base: int = 2,
        use_tls: bool = True
    ):
        """
        Inicializa el servicio de email.
        
        Args:
            smtp_host: Host del servidor SMTP
            smtp_port: Puerto del servidor SMTP
            username: Usuario para autenticación
            password: Contraseña para autenticación
            max_reintentos: Número máximo de reintentos
            delay_base: Delay base en segundos para exponential backoff (2, 4, 8...)
            use_tls: Si True, usa TLS (recomendado)
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.max_reintentos = max_reintentos
        self.delay_base = delay_base
        self.use_tls = use_tls
        
        # Estadísticas
        self.stats = {
            'enviados': 0,
            'fallidos': 0,
            'reintentos_aplicados': 0,
            'errores': []
        }
    
    def enviar_con_reintentos(
        self,
        destinatario: str,
        asunto: str,
        cuerpo: str,
        html: bool = True,
        adjuntos: Optional[List[Dict]] = None,
        remitente: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> Dict:
        """
        Envía email con reintentos automáticos usando exponential backoff.
        
        Args:
            destinatario: Email del destinatario
            asunto: Asunto del email
            cuerpo: Contenido del email
            html: Si True, cuerpo es HTML
            adjuntos: Lista de dicts con {'ruta': path, 'nombre': filename}
            remitente: Remitente (por defecto usa username)
            cc: Lista de emails en CC
            bcc: Lista de emails en BCC
        
        Returns:
            Dict con:
            {
                'exito': bool,
                'intento': int,
                'mensaje': str,
                'error': str (si aplica),
                'id_mensaje': str (si aplica)
            }
        """
        
        remitente = remitente or self.username
        
        for intento in range(1, self.max_reintentos + 1):
            try:
                logger.info(f"Enviando email a {destinatario} (intento {intento}/{self.max_reintentos})")
                
                # Construir mensaje
                mensaje = self._construir_mensaje(
                    remitente=remitente,
                    destinatario=destinatario,
                    asunto=asunto,
                    cuerpo=cuerpo,
                    html=html,
                    cc=cc,
                    bcc=bcc
                )
                
                # Adjuntos
                if adjuntos:
                    for adjunto in adjuntos:
                        self._adjuntar_archivo(mensaje, adjunto)
                
                # Enviar
                resultado = self._enviar_smtp(
                    mensaje=mensaje,
                    remitente=remitente,
                    destinatarios=[destinatario] + (cc or []) + (bcc or [])
                )
                
                # Éxito
                self.stats['enviados'] += 1
                logger.info(f"✓ Email enviado a {destinatario} en intento {intento}")
                
                return {
                    'exito': True,
                    'intento': intento,
                    'mensaje': f"Email enviado exitosamente en intento {intento}",
                    'error': None
                }
            
            except smtplib.SMTPTemporaryError as e:
                # Error temporal (429, 450, etc) - reintentar
                logger.warning(f"Error temporal SMTP: {e}")
                
                if intento < self.max_reintentos:
                    delay = self.delay_base ** intento
                    logger.info(f"Reintentando en {delay} segundos...")
                    self.stats['reintentos_aplicados'] += 1
                    time.sleep(delay)
                else:
                    # Falló después de todos los reintentos
                    self.stats['fallidos'] += 1
                    error_msg = f"Error temporal SMTP después de {self.max_reintentos} intentos: {str(e)}"
                    logger.error(error_msg)
                    self.stats['errores'].append({
                        'destinatario': destinatario,
                        'error': error_msg,
                        'tipo': 'SMTPTemporaryError'
                    })
                    
                    return {
                        'exito': False,
                        'intento': intento,
                        'mensaje': f"Falló después de {self.max_reintentos} intentos",
                        'error': error_msg
                    }
            
            except smtplib.SMTPAuthenticationError as e:
                # Error de autenticación - NO reintentar
                self.stats['fallidos'] += 1
                error_msg = f"Error de autenticación SMTP: {str(e)}"
                logger.error(error_msg)
                self.stats['errores'].append({
                    'destinatario': destinatario,
                    'error': error_msg,
                    'tipo': 'SMTPAuthenticationError'
                })
                
                return {
                    'exito': False,
                    'intento': intento,
                    'mensaje': "Error de autenticación",
                    'error': error_msg
                }
            
            except Exception as e:
                # Error desconocido - reintentar si aplica
                logger.error(f"Error en envío de email: {e}", exc_info=True)
                
                if intento < self.max_reintentos:
                    delay = self.delay_base ** intento
                    logger.info(f"Reintentando en {delay} segundos...")
                    self.stats['reintentos_aplicados'] += 1
                    time.sleep(delay)
                else:
                    self.stats['fallidos'] += 1
                    error_msg = f"Error desconocido: {str(e)}"
                    self.stats['errores'].append({
                        'destinatario': destinatario,
                        'error': error_msg,
                        'tipo': 'UnknownError'
                    })
                    
                    return {
                        'exito': False,
                        'intento': intento,
                        'mensaje': f"Error después de {self.max_reintentos} intentos",
                        'error': error_msg
                    }
        
        return {
            'exito': False,
            'intento': self.max_reintentos,
            'mensaje': f"Falló después de todos los reintentos",
            'error': 'Máximo de reintentos excedido'
        }
    
    def _construir_mensaje(
        self,
        remitente: str,
        destinatario: str,
        asunto: str,
        cuerpo: str,
        html: bool = True,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> MIMEMultipart:
        """Construye el mensaje MIME."""
        
        mensaje = MIMEMultipart('alternative')
        mensaje['Subject'] = asunto
        mensaje['From'] = remitente
        mensaje['To'] = destinatario
        
        if cc:
            mensaje['Cc'] = ', '.join(cc)
        
        # Agregar cuerpo
        tipo_contenido = 'html' if html else 'plain'
        parte = MIMEText(cuerpo, tipo_contenido, 'utf-8')
        mensaje.attach(parte)
        
        return mensaje
    
    def _adjuntar_archivo(self, mensaje: MIMEMultipart, adjunto: Dict):
        """Adjunta un archivo al mensaje."""
        
        try:
            ruta = adjunto['ruta']
            nombre = adjunto.get('nombre', ruta.split('/')[-1])
            
            with open(ruta, 'rb') as attachment:
                parte = MIMEBase('application', 'octet-stream')
                parte.set_payload(attachment.read())
            
            encoders.encode_base64(parte)
            parte.add_header('Content-Disposition', 'attachment', filename=nombre)
            mensaje.attach(parte)
            
            logger.debug(f"Adjunto agregado: {nombre}")
        
        except Exception as e:
            logger.error(f"Error al adjuntar archivo: {e}")
            raise
    
    def _enviar_smtp(
        self,
        mensaje: MIMEMultipart,
        remitente: str,
        destinatarios: List[str]
    ) -> bool:
        """Envía el mensaje via SMTP."""
        
        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as servidor:
            if self.use_tls:
                servidor.starttls()
            
            servidor.login(self.username, self.password)
            servidor.send_message(mensaje)
        
        return True
    
    def obtener_estadisticas(self) -> Dict:
        """Retorna estadísticas de envíos."""
        return {
            'enviados': self.stats['enviados'],
            'fallidos': self.stats['fallidos'],
            'reintentos_aplicados': self.stats['reintentos_aplicados'],
            'total_intentos': self.stats['enviados'] + self.stats['fallidos'],
            'tasa_exito': round(
                (self.stats['enviados'] / max(1, self.stats['enviados'] + self.stats['fallidos'])) * 100,
                2
            ),
            'errores_totales': len(self.stats['errores'])
        }
    
    def resetear_estadisticas(self):
        """Resetea las estadísticas."""
        self.stats = {
            'enviados': 0,
            'fallidos': 0,
            'reintentos_aplicados': 0,
            'errores': []
        }


# Uso de ejemplo:
# 
# service = EmailServiceConReintentos(
#     smtp_host='smtp.gmail.com',
#     smtp_port=587,
#     username='noreply@rapicredit.com',
#     password='APP_PASSWORD',
#     max_reintentos=3,
#     delay_base=2
# )
# 
# resultado = service.enviar_con_reintentos(
#     destinatario='cliente@example.com',
#     asunto='Notificación de vencimiento',
#     cuerpo='<h1>Tu cuota vence mañana</h1>',
#     html=True,
#     adjuntos=[{'ruta': '/tmp/recibo.pdf', 'nombre': 'recibo.pdf'}],
#     cc=['supervisor@rapicredit.com']
# )
# 
# if resultado['exito']:
#     print(f"✓ Enviado en intento {resultado['intento']}")
# else:
#     print(f"✗ Error: {resultado['error']}")
#
# print(service.obtener_estadisticas())
