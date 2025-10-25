# backend/app/models/configuracion_sistema.py
"""
Modelo de Configuración del Sistema
Centraliza todas las configuraciones del sistema para fácil gestión desde el frontend
"""
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.db.session import Base

logger = logging.getLogger(__name__)


class ConfiguracionSistema(Base):
    """
    Configuración centralizada del sistema
    Permite configurar desde el frontend todos los aspectos del sistema
    """

    __tablename__ = "configuracion_sistema"

    id = Column(Integer, primary_key=True, index=True)
    categoria = Column(
        String(50), nullable=False, index=True
    )  # AI, EMAIL, WHATSAPP, etc.
    subcategoria = Column(
        String(50), nullable=True, index=True
    )  # OPENAI, GMAIL, TWILIO, etc.
    clave = Column(
        String(100), nullable=False, index=True
    )  # Nombre de la configuración
    valor = Column(Text, nullable=True)  # Valor de la configuración
    valor_json = Column(JSON, nullable=True)  # Para configuraciones complejas

    # Metadatos
    descripcion = Column(Text, nullable=True)
    tipo_dato = Column(
        String(20), default="STRING"
    )  # STRING, INTEGER, BOOLEAN, JSON, PASSWORD
    requerido = Column(Boolean, default=False)
    visible_frontend = Column(Boolean, default=True)
    solo_lectura = Column(Boolean, default=False)

    # Validaciones
    valor_minimo = Column(String(100), nullable=True)
    valor_maximo = Column(String(100), nullable=True)
    opciones_validas = Column(
        Text, nullable=True
    )  # JSON array de opciones válidas
    patron_validacion = Column(
        String(200), nullable=True
    )  # Regex para validación

    # Auditoría
    creado_en = Column(DateTime, server_default=func.now())
    actualizado_en = Column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    actualizado_por = Column(String(100), nullable=True)

    def __repr__(self):
        return f"<ConfiguracionSistema({self.categoria}.{self.clave}={self.valor})>"

    def _procesar_valor_boolean(self) -> bool:
        """Procesar valor de tipo BOOLEAN"""
        return (
            self.valor.lower() in ["true", "1", "yes", "on"]
            if self.valor
            else False
        )

    def _procesar_valor_integer(self) -> int:
        """Procesar valor de tipo INTEGER"""
        try:
            return int(self.valor) if self.valor else 0
        except (ValueError, TypeError):
            return 0

    def _procesar_valor_decimal(self) -> float:
        """Procesar valor de tipo DECIMAL"""
        try:
            return float(self.valor) if self.valor else 0.0
        except (ValueError, TypeError):
            return 0.0

    def _procesar_valor_json(self) -> dict:
        """Procesar valor de tipo JSON"""
        try:
            return json.loads(self.valor) if self.valor else {}
        except (json.JSONDecodeError, TypeError):
            return self.valor_json or {}

    def _procesar_valor_string(self) -> str:
        """Procesar valor de tipo STRING"""
        return self.valor or ""

    @property
    def valor_procesado(self):
        """Obtener valor procesado según el tipo de dato (VERSIÓN REFACTORIZADA)"""
        if self.tipo_dato == "BOOLEAN":
            return self._procesar_valor_boolean()
        elif self.tipo_dato == "INTEGER":
            return self._procesar_valor_integer()
        elif self.tipo_dato == "DECIMAL":
            return self._procesar_valor_decimal()
        elif self.tipo_dato == "JSON":
            return self._procesar_valor_json()
        else:
            return self._procesar_valor_string()

    def actualizar_valor(self, nuevo_valor: Any, usuario: str = None):
        """Actualizar valor con validación"""
        # Validar según tipo
        if self.tipo_dato == "BOOLEAN":
            self.valor = str(bool(nuevo_valor)).lower()
        elif self.tipo_dato == "INTEGER":
            self.valor = str(int(nuevo_valor))
        elif self.tipo_dato == "DECIMAL":
            self.valor = str(float(nuevo_valor))
        elif self.tipo_dato == "JSON":
            if isinstance(nuevo_valor, (dict, list)):
                self.valor_json = nuevo_valor
                self.valor = json.dumps(nuevo_valor)
            else:
                self.valor = str(nuevo_valor)
        else:
            self.valor = str(nuevo_valor)

        self.actualizado_en = datetime.utcnow()
        if usuario:
            self.actualizado_por = usuario

    @staticmethod
    def obtener_por_clave(
        db, categoria: str, clave: str
    ) -> Optional["ConfiguracionSistema"]:
        """Obtener configuración por categoría y clave"""
        return (
            db.query(ConfiguracionSistema)
            .filter(
                ConfiguracionSistema.categoria == categoria,
                ConfiguracionSistema.clave == clave,
            )
            .first()
        )

    @staticmethod
    def obtener_categoria(db, categoria: str) -> Dict[str, Any]:
        """Obtener todas las configuraciones de una categoría"""
        configs = (
            db.query(ConfiguracionSistema)
            .filter(ConfiguracionSistema.categoria == categoria)
            .all()
        )

        resultado = {}
        for config in configs:
            resultado[config.clave] = {
                "valor": config.valor_procesado,
                "descripcion": config.descripcion,
                "tipo": config.tipo_dato,
                "requerido": config.requerido,
            }

        return resultado


class ConfiguracionPorDefecto:
    """
    Configuraciones por defecto del sistema
    Se crean automáticamente al inicializar el sistema
    """

    CONFIGURACIONES_DEFAULT = {
        # ============================================
        # INTELIGENCIA ARTIFICIAL
        # ============================================
        "AI": {
            "OPENAI_API_KEY": {
                "valor": "",
                "descripcion": "Token de API de OpenAI para funcionalidades de IA",
                "tipo_dato": "PASSWORD",
                "requerido": False,
                "visible_frontend": True,
                "patron_validacion": r"^sk-[a-zA-Z0-9]{48}$",
            },
            "OPENAI_MODEL": {
                "valor": "gpt-3.5-turbo",
                "descripcion": "Modelo de OpenAI a utilizar",
                "tipo_dato": "STRING",
                "opciones_validas": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"],
                "requerido": False,
            },
            "AI_SCORING_ENABLED": {
                "valor": "true",
                "descripcion": "Habilitar scoring crediticio con IA",
                "tipo_dato": "BOOLEAN",
                "requerido": False,
            },
            "AI_PREDICTION_ENABLED": {
                "valor": "true",
                "descripcion": "Habilitar predicción de mora con ML",
                "tipo_dato": "BOOLEAN",
                "requerido": False,
            },
            "AI_CHATBOT_ENABLED": {
                "valor": "true",
                "descripcion": "Habilitar chatbot inteligente",
                "tipo_dato": "BOOLEAN",
                "requerido": False,
            },
        },
        # ============================================
        # CONFIGURACIÓN DE EMAIL
        # ============================================
        "EMAIL": {
            "SMTP_HOST": {
                "valor": "smtp.gmail.com",
                "descripcion": "Servidor SMTP para envío de emails",
                "tipo_dato": "STRING",
                "requerido": True,
                "visible_frontend": True,
            },
            "SMTP_PORT": {
                "valor": "587",
                "descripcion": "Puerto SMTP",
                "tipo_dato": "INTEGER",
                "valor_minimo": "1",
                "valor_maximo": "65535",
                "requerido": True,
            },
            "SMTP_USERNAME": {
                "valor": "",
                "descripcion": "Usuario SMTP (email de la empresa)",
                "tipo_dato": "STRING",
                "requerido": True,
                "patron_validacion": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            },
            "SMTP_PASSWORD": {
                "valor": "",
                "descripcion": "Contraseña SMTP o App Password",
                "tipo_dato": "PASSWORD",
                "requerido": True,
                "visible_frontend": True,
            },
            "EMAIL_FROM_NAME": {
                "valor": "Sistema de Financiamiento",
                "descripcion": "Nombre que aparece como remitente",
                "tipo_dato": "STRING",
                "requerido": True,
            },
            "EMAIL_TEMPLATES_ENABLED": {
                "valor": "true",
                "descripcion": "Usar templates HTML profesionales",
                "tipo_dato": "BOOLEAN",
                "requerido": False,
            },
        },
        # ============================================
        # CONFIGURACIÓN DE WHATSAPP MULTICANAL
        # ============================================
        "WHATSAPP": {
            "WHATSAPP_ENABLED": {
                "valor": "false",
                "descripcion": "Habilitar notificaciones por WhatsApp",
                "tipo_dato": "BOOLEAN",
                "requerido": False,
            },
            "WHATSAPP_PROVIDER": {
                "valor": "META_CLOUD_API",
                "descripcion": "Proveedor de WhatsApp Business API",
                "tipo_dato": "STRING",
                "opciones_validas": ["META_CLOUD_API"],
                "requerido": False,
            },
            # CONFIGURACIÓN META CLOUD API
            "META_ACCESS_TOKEN": {
                "valor": "",
                "descripcion": "Access Token de Meta Cloud API",
                "tipo_dato": "PASSWORD",
                "requerido": False,
                "visible_frontend": True,
            },
            "META_PHONE_NUMBER_ID": {
                "valor": "",
                "descripcion": "Phone Number ID de Meta",
                "tipo_dato": "STRING",
                "requerido": False,
                "visible_frontend": True,
            },
            # CONFIGURACIÓN GENERAL
            "WHATSAPP_FROM_NUMBER": {
                "valor": "",
                "descripcion": "Número de WhatsApp Business (formato: +1234567890)",
                "tipo_dato": "STRING",
                "patron_validacion": r"^\+[1-9]\d{1,14}$",
                "requerido": False,
            },
            "WHATSAPP_BUSINESS_NAME": {
                "valor": "Financiamiento Automotriz",
                "descripcion": "Nombre del negocio en WhatsApp",
                "tipo_dato": "STRING",
                "requerido": False,
            },
            "WHATSAPP_WEBHOOK_URL": {
                "valor": "",
                "descripcion": "URL del webhook para recibir respuestas",
                "tipo_dato": "STRING",
                "requerido": False,
            },
            "WHATSAPP_VERIFY_TOKEN": {
                "valor": "",
                "descripcion": "Token de verificación del webhook",
                "tipo_dato": "PASSWORD",
                "requerido": False,
            },
        },
        # ============================================
        # CONFIGURACIÓN DE ROLES Y PERMISOS
        # ============================================
        "ROLES": {
            "ROLES_ACTIVOS": {
                "valor_json": ["USER"],
                "descripcion": "Roles activos en el sistema",
                "tipo_dato": "JSON",
                "requerido": True,
                "visible_frontend": True,
            },
            "REGISTRO_USUARIOS_ABIERTO": {
                "valor": "false",
                "descripcion": "Permitir registro abierto de usuarios",
                "tipo_dato": "BOOLEAN",
                "requerido": False,
            },
            "REQUIERE_APROBACION_USUARIOS": {
                "valor": "true",
                "descripcion": "Nuevos usuarios requieren aprobación de admin",
                "tipo_dato": "BOOLEAN",
                "requerido": False,
            },
            "SESION_DURACION_HORAS": {
                "valor": "8",
                "descripcion": "Duración de sesión en horas",
                "tipo_dato": "INTEGER",
                "valor_minimo": "1",
                "valor_maximo": "24",
                "requerido": True,
            },
        },
        # ============================================
        # CONFIGURACIÓN FINANCIERA
        # ============================================
        "FINANCIERO": {
            "TASA_INTERES_BASE": {
                "valor": "18.0",
                "descripcion": "Tasa de interés base anual (%)",
                "tipo_dato": "DECIMAL",
                "valor_minimo": "5.0",
                "valor_maximo": "50.0",
                "requerido": True,
            },
            "TASA_MORA_MENSUAL": {
                "valor": "2.0",
                "descripcion": "Tasa de mora mensual (%)",
                "tipo_dato": "DECIMAL",
                "valor_minimo": "0.5",
                "valor_maximo": "10.0",
                "requerido": True,
            },
            "CUOTA_INICIAL_MINIMA": {
                "valor": "10.0",
                "descripcion": "Cuota inicial mínima (%)",
                "tipo_dato": "DECIMAL",
                "valor_minimo": "0.0",
                "valor_maximo": "50.0",
                "requerido": True,
            },
            "MONTO_MAXIMO_FINANCIAMIENTO": {
                "valor": "5000000",
                "descripcion": "Monto máximo de financiamiento",
                "tipo_dato": "INTEGER",
                "valor_minimo": "1",
                "valor_maximo": "50000000",
                "requerido": True,
            },
            "PLAZO_MAXIMO_MESES": {
                "valor": "84",
                "descripcion": "Plazo máximo en meses",
                "tipo_dato": "INTEGER",
                "valor_minimo": "12",
                "valor_maximo": "120",
                "requerido": True,
            },
        },
        # ============================================
        # CONFIGURACIÓN DE NOTIFICACIONES
        # ============================================
        "NOTIFICACIONES": {
            "RECORDATORIOS_HABILITADOS": {
                "valor": "true",
                "descripcion": "Habilitar recordatorios automáticos",
                "tipo_dato": "BOOLEAN",
                "requerido": False,
            },
            "DIAS_ANTES_RECORDATORIO": {
                "valor": "3",
                "descripcion": "Días antes del vencimiento para recordatorio",
                "tipo_dato": "INTEGER",
                "valor_minimo": "1",
                "valor_maximo": "10",
                "requerido": False,
            },
            "NOTIFICACIONES_MORA_HABILITADAS": {
                "valor": "true",
                "descripcion": "Habilitar notificaciones de mora",
                "tipo_dato": "BOOLEAN",
                "requerido": False,
            },
            "FRECUENCIA_NOTIFICACIONES_MORA": {
                "valor": "DIARIA",
                "descripcion": "Frecuencia de notificaciones de mora",
                "tipo_dato": "STRING",
                "opciones_validas": ["DIARIA", "SEMANAL", "QUINCENAL"],
                "requerido": False,
            },
        },
        # ============================================
        # CONFIGURACIÓN DE SEGURIDAD
        # ============================================
        "SEGURIDAD": {
            "JWT_SECRET_KEY": {
                "valor": "",
                "descripcion": "Clave secreta para JWT (se genera automáticamente)",
                "tipo_dato": "PASSWORD",
                "requerido": True,
                "solo_lectura": True,
                "visible_frontend": False,
            },
            "JWT_EXPIRATION_HOURS": {
                "valor": "8",
                "descripcion": "Expiración de tokens JWT en horas",
                "tipo_dato": "INTEGER",
                "valor_minimo": "1",
                "valor_maximo": "72",
                "requerido": True,
            },
            "INTENTOS_LOGIN_MAXIMOS": {
                "valor": "5",
                "descripcion": "Intentos máximos de login antes de bloqueo",
                "tipo_dato": "INTEGER",
                "valor_minimo": "3",
                "valor_maximo": "10",
                "requerido": True,
            },
            "BLOQUEO_DURACION_MINUTOS": {
                "valor": "30",
                "descripcion": "Duración del bloqueo en minutos",
                "tipo_dato": "INTEGER",
                "valor_minimo": "5",
                "valor_maximo": "1440",
                "requerido": True,
            },
        },
        # ============================================
        # CONFIGURACIÓN DE BASE DE DATOS
        # ============================================
        "DATABASE": {
            "BACKUP_AUTOMATICO": {
                "valor": "true",
                "descripcion": "Habilitar backup automático diario",
                "tipo_dato": "BOOLEAN",
                "requerido": False,
            },
            "BACKUP_HORA": {
                "valor": "02:00",
                "descripcion": "Hora para backup automático (HH:MM)",
                "tipo_dato": "STRING",
                "patron_validacion": r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$",
                "requerido": False,
            },
            "RETENTION_LOGS_DIAS": {
                "valor": "90",
                "descripcion": "Días de retención de logs",
                "tipo_dato": "INTEGER",
                "valor_minimo": "30",
                "valor_maximo": "365",
                "requerido": False,
            },
        },
        # ============================================
        # CONFIGURACIÓN DE REPORTES
        # ============================================
        "REPORTES": {
            "LOGO_EMPRESA": {
                "valor": "",
                "descripcion": "URL del logo para reportes PDF",
                "tipo_dato": "STRING",
                "requerido": False,
            },
            "NOMBRE_EMPRESA": {
                "valor": "Financiamiento Automotriz",
                "descripcion": "Nombre de la empresa en reportes",
                "tipo_dato": "STRING",
                "requerido": True,
            },
            "DIRECCION_EMPRESA": {
                "valor": "",
                "descripcion": "Dirección de la empresa",
                "tipo_dato": "TEXT",
                "requerido": False,
            },
            "TELEFONO_EMPRESA": {
                "valor": "",
                "descripcion": "Teléfono de la empresa",
                "tipo_dato": "STRING",
                "requerido": False,
            },
            "REPORTES_AUTOMATICOS": {
                "valor": "true",
                "descripcion": "Generar reportes automáticos",
                "tipo_dato": "BOOLEAN",
                "requerido": False,
            },
        },
        # ============================================
        # CONFIGURACIÓN DE INTEGRACIONES
        # ============================================
        "INTEGRACIONES": {
            "DATACREDITO_ENABLED": {
                "valor": "false",
                "descripcion": "Habilitar integración con DataCrédito",
                "tipo_dato": "BOOLEAN",
                "requerido": False,
            },
            "DATACREDITO_API_KEY": {
                "valor": "",
                "descripcion": "API Key de DataCrédito",
                "tipo_dato": "PASSWORD",
                "requerido": False,
                "visible_frontend": True,
            },
            "PASARELA_PAGOS_ENABLED": {
                "valor": "false",
                "descripcion": "Habilitar pasarela de pagos online",
                "tipo_dato": "BOOLEAN",
                "requerido": False,
            },
            "PASARELA_PAGOS_PROVIDER": {
                "valor": "STRIPE",
                "descripcion": "Proveedor de pasarela de pagos",
                "tipo_dato": "STRING",
                "opciones_validas": [
                    "STRIPE",
                    "PAYPAL",
                    "MERCADOPAGO",
                    "CARDNET",
                ],
                "requerido": False,
            },
        },
        # ============================================
        # CONFIGURACIÓN DE MONITOREO
        # ============================================
        "MONITOREO": {
            "SENTRY_DSN": {
                "valor": "",
                "descripcion": "DSN de Sentry para tracking de errores",
                "tipo_dato": "STRING",
                "requerido": False,
                "visible_frontend": True,
            },
            "PROMETHEUS_ENABLED": {
                "valor": "false",
                "descripcion": "Habilitar métricas de Prometheus",
                "tipo_dato": "BOOLEAN",
                "requerido": False,
            },
            "LOG_LEVEL": {
                "valor": "INFO",
                "descripcion": "Nivel de logging",
                "tipo_dato": "STRING",
                "opciones_validas": [
                    "DEBUG",
                    "INFO",
                    "WARNING",
                    "ERROR",
                    "CRITICAL",
                ],
                "requerido": True,
            },
        },
        # ============================================
        # CONFIGURACIÓN DE LA APLICACIÓN
        # ============================================
        "APLICACION": {
            "NOMBRE_SISTEMA": {
                "valor": "Sistema de Financiamiento Automotriz",
                "descripcion": "Nombre del sistema",
                "tipo_dato": "STRING",
                "requerido": True,
                "visible_frontend": True,
            },
            "VERSION_SISTEMA": {
                "valor": "1.0.0",
                "descripcion": "Versión actual del sistema",
                "tipo_dato": "STRING",
                "solo_lectura": True,
                "visible_frontend": True,
            },
            "MANTENIMIENTO_PROGRAMADO": {
                "valor": "false",
                "descripcion": "Modo mantenimiento programado",
                "tipo_dato": "BOOLEAN",
                "requerido": False,
            },
            "MENSAJE_MANTENIMIENTO": {
                "valor": "Sistema en mantenimiento. Vuelva en unos minutos.",
                "descripcion": "Mensaje durante mantenimiento",
                "tipo_dato": "TEXT",
                "requerido": False,
            },
            "TIMEZONE": {
                "valor": "America/Santo_Domingo",
                "descripcion": "Zona horaria del sistema",
                "tipo_dato": "STRING",
                "opciones_validas": [
                    "America/Santo_Domingo",
                    "America/New_York",
                    "America/Mexico_City",
                    "UTC",
                ],
                "requerido": True,
            },
        },
    }

    @staticmethod
    def crear_configuraciones_default(db):
        """Crear configuraciones por defecto si no existen"""
        try:
            for (
                categoria,
                configs,
            ) in ConfiguracionPorDefecto.CONFIGURACIONES_DEFAULT.items():
                for clave, config_data in configs.items():
                    # Verificar si ya existe
                    existing = (
                        db.query(ConfiguracionSistema)
                        .filter(
                            ConfiguracionSistema.categoria == categoria,
                            ConfiguracionSistema.clave == clave,
                        )
                        .first()
                    )

                    if not existing:
                        # Crear nueva configuración
                        nueva_config = ConfiguracionSistema(
                            categoria=categoria,
                            clave=clave,
                            valor=config_data.get("valor", ""),
                            valor_json=config_data.get("valor_json"),
                            descripcion=config_data.get("descripcion", ""),
                            tipo_dato=config_data.get("tipo_dato", "STRING"),
                            requerido=config_data.get("requerido", False),
                            visible_frontend=config_data.get(
                                "visible_frontend", True
                            ),
                            solo_lectura=config_data.get(
                                "solo_lectura", False
                            ),
                            opciones_validas=(
                                json.dumps(config_data.get("opciones_validas"))
                                if config_data.get("opciones_validas")
                                else None
                            ),
                            patron_validacion=config_data.get(
                                "patron_validacion"
                            ),
                            valor_minimo=config_data.get("valor_minimo"),
                            valor_maximo=config_data.get("valor_maximo"),
                        )

                        db.add(nueva_config)

            db.commit()
            logger = logging.getLogger(__name__)
            logger.info("Configuraciones por defecto creadas exitosamente")

        except Exception as e:
            db.rollback()
            logger = logging.getLogger(__name__)
            logger.error(f"Error creando configuraciones por defecto: {e}")


# ============================================
# HELPER PARA ACCESO RÁPIDO A CONFIGURACIONES
# ============================================


class ConfigHelper:
    """
    Helper para acceso rápido a configuraciones
    """

    @staticmethod
    def get_config(db, categoria: str, clave: str, default=None):
        """Obtener valor de configuración"""
        config = ConfiguracionSistema.obtener_por_clave(db, categoria, clave)
        if config:
            return config.valor_procesado
        return default

    @staticmethod
    def is_ai_enabled(db) -> bool:
        """Verificar si IA está habilitada"""
        return ConfigHelper.get_config(db, "AI", "AI_SCORING_ENABLED", False)

    @staticmethod
    def is_email_configured(db) -> bool:
        """Verificar si email está configurado"""
        smtp_host = ConfigHelper.get_config(db, "EMAIL", "SMTP_HOST")
        smtp_user = ConfigHelper.get_config(db, "EMAIL", "SMTP_USERNAME")
        return bool(smtp_host and smtp_user)

    @staticmethod
    def is_whatsapp_enabled(db) -> bool:
        """Verificar si WhatsApp está habilitado"""
        return ConfigHelper.get_config(
            db, "WHATSAPP", "WHATSAPP_ENABLED", False
        )

    @staticmethod
    def get_financial_config(db) -> Dict:
        """Obtener configuración financiera completa"""
        return {
            "tasa_base": ConfigHelper.get_config(
                db, "FINANCIERO", "TASA_INTERES_BASE", 18.0
            ),
            "tasa_mora": ConfigHelper.get_config(
                db, "FINANCIERO", "TASA_MORA_MENSUAL", 2.0
            ),
            "cuota_inicial_min": ConfigHelper.get_config(
                db, "FINANCIERO", "CUOTA_INICIAL_MINIMA", 10.0
            ),
            "monto_maximo": ConfigHelper.get_config(
                db, "FINANCIERO", "MONTO_MAXIMO_FINANCIAMIENTO", 5000000
            ),
            "plazo_maximo": ConfigHelper.get_config(
                db, "FINANCIERO", "PLAZO_MAXIMO_MESES", 84
            ),
        }

    @staticmethod
    def get_notification_config(db) -> Dict:
        """Obtener configuración de notificaciones"""
        return {
            "recordatorios": ConfigHelper.get_config(
                db, "NOTIFICACIONES", "RECORDATORIOS_HABILITADOS", True
            ),
            "dias_antes": ConfigHelper.get_config(
                db, "NOTIFICACIONES", "DIAS_ANTES_RECORDATORIO", 3
            ),
            "mora_habilitada": ConfigHelper.get_config(
                db, "NOTIFICACIONES", "NOTIFICACIONES_MORA_HABILITADAS", True
            ),
            "frecuencia_mora": ConfigHelper.get_config(
                db,
                "NOTIFICACIONES",
                "FRECUENCIA_NOTIFICACIONES_MORA",
                "DIARIA",
            ),
        }
