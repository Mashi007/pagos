from datetime import date
# backend/app/models/configuracion_sistema.py
"""Modelo de Configuración del Sistema

Centraliza todas las configuraciones del sistema para fácil gestión desde
el frontend
"""

import json
import logging
from typing import Any, Dict, Optional
from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func
from app.db.session import Base

logger = logging.getLogger(__name__)


class ConfiguracionSistema(Base):
    """
    Configuración centralizada del sistema
    """
    __tablename__ = "configuracion_sistema"

    id = Column(Integer, primary_key=True, index=True)
    categoria = Column
        String(50), nullable=False, index=True
    )  # AI, EMAIL, WHATSAPP, etc.
    subcategoria = Column
        String(50), nullable=True, index=True
    )  # OPENAI, GMAIL, TWILIO, etc.
    clave = Column
        String(100), nullable=False, index=True
    )  # Nombre de la configuración
    valor = Column(Text, nullable=True)  # Valor de la configuración
    valor_json = Column(JSON, nullable=True)  # Para configuraciones complejas

    descripcion = Column(Text, nullable=True)
    tipo_dato = Column
        String(20), default="STRING"
    )  # STRING, INTEGER, BOOLEAN, JSON, PASSWORD
    requerido = Column(Boolean, default=False)
    visible_frontend = Column(Boolean, default=True)
    solo_lectura = Column(Boolean, default=False)

    # Validaciones
    valor_minimo = Column(String(100), nullable=True)
    valor_maximo = Column(String(100), nullable=True)
    opciones_validas = Column(Text, nullable=True)  # JSON array de opciones válidas
    patron_validacion = Column
        String(200), nullable=True
    )  # Regex para validación

    # Auditoría
    creado_en = Column(DateTime, server_default=func.now())
    actualizado_en = Column
        DateTime, server_default=func.now(), onupdate=func.now()
    actualizado_por = Column(String(100), nullable=True)


    def __repr__(self):
        return f"<ConfiguracionSistema({self.categoria}.{self.clave}={self.valor})>"


    def _procesar_valor_boolean(self) -> bool:
        """Procesar valor de tipo BOOLEAN"""
        return 
            self.valor.lower() in ["true", "1", "yes", "on"]
            if self.valor
            else False


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

        if usuario:
            self.actualizado_por = usuario

    @staticmethod
    def obtener_por_clave
    ) -> Optional["ConfiguracionSistema"]:
        """Obtener configuración por categoría y clave"""
        return 
            db.query(ConfiguracionSistema)
            .filter
            .first()

    @staticmethod
    def obtener_categoria(db, categoria: str) -> Dict[str, Any]:
        """Obtener todas las configuraciones de una categoría"""
        configs = 
            db.query(ConfiguracionSistema)
            .filter(ConfiguracionSistema.categoria == categoria)
            .all()
        resultado = {}
        for config in configs:
            resultado[config.clave] = 
        return resultado


class ConfiguracionPorDefecto:
    """
    Configuraciones por defecto del sistema
    Se crean automáticamente al inicializar el sistema
    """
    CONFIGURACIONES_DEFAULT = 
                "patron_validacion": r"^sk-[a-zA-Z0-9]{48}$",
            },
            "OPENAI_MODEL": 
            },
            "AI_SCORING_ENABLED": 
            },
            "AI_PREDICTION_ENABLED": 
            },
            "AI_CHATBOT_ENABLED": 
            },
        },
        # ============================================
        # CONFIGURACIÓN DE EMAIL
        # ============================================
        "EMAIL": 
            },
            "SMTP_PORT": 
            },
            "SMTP_USERNAME": 
                "patron_validacion": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            },
            "SMTP_PASSWORD": 
            },
            "EMAIL_FROM_NAME": 
            },
            "EMAIL_TEMPLATES_ENABLED": 
            },
        },
        # ============================================
        # CONFIGURACIÓN DE WHATSAPP MULTICANAL
        # ============================================
        "WHATSAPP": 
            },
            "WHATSAPP_PROVIDER": 
            },
            # CONFIGURACIÓN META CLOUD API
            "META_ACCESS_TOKEN": 
            },
            "META_PHONE_NUMBER_ID": 
            },
            # CONFIGURACIÓN GENERAL
            "WHATSAPP_FROM_NUMBER": 
                "patron_validacion": r"^\+[1-9]\d{1,14}$",
                "requerido": False,
            },
            "WHATSAPP_BUSINESS_NAME": 
            },
            "WHATSAPP_WEBHOOK_URL": 
            },
            "WHATSAPP_VERIFY_TOKEN": 
            },
        },
        # ============================================
        # CONFIGURACIÓN DE ROLES Y PERMISOS
        # ============================================
        "ROLES": 
            },
            "REGISTRO_USUARIOS_ABIERTO": 
            },
            "REQUIERE_APROBACION_USUARIOS": 
            },
            "SESION_DURACION_HORAS": 
            },
        },
        # ============================================
        # CONFIGURACIÓN FINANCIERA
        # ============================================
        "FINANCIERO": 
            },
            "TASA_MORA_MENSUAL": 
            },
            "CUOTA_INICIAL_MINIMA": 
            },
            "MONTO_MAXIMO_FINANCIAMIENTO": 
            },
            "PLAZO_MAXIMO_MESES": 
            },
        },
        # ============================================
        # CONFIGURACIÓN DE NOTIFICACIONES
        # ============================================
        "NOTIFICACIONES": 
            },
            "DIAS_ANTES_RECORDATORIO": 
            },
            "NOTIFICACIONES_MORA_HABILITADAS": 
            },
            "FRECUENCIA_NOTIFICACIONES_MORA": 
            },
        },
        # ============================================
        # CONFIGURACIÓN DE SEGURIDAD
        # ============================================
        "SEGURIDAD": 
            },
            "JWT_EXPIRATION_HOURS": 
            },
            "INTENTOS_LOGIN_MAXIMOS": 
            },
            "BLOQUEO_DURACION_MINUTOS": 
            },
        },
        # ============================================
        # CONFIGURACIÓN DE BASE DE DATOS
        # ============================================
        "DATABASE": 
            },
            "BACKUP_HORA": 
            },
            "RETENTION_LOGS_DIAS": 
            },
        },
        # ============================================
        # CONFIGURACIÓN DE REPORTES
        # ============================================
        "REPORTES": 
            },
            "NOMBRE_EMPRESA": 
            },
            "DIRECCION_EMPRESA": 
            },
            "TELEFONO_EMPRESA": 
            },
            "REPORTES_AUTOMATICOS": 
            },
        },
        # ============================================
        # CONFIGURACIÓN DE INTEGRACIONES
        # ============================================
        "INTEGRACIONES": 
            },
            "DATACREDITO_API_KEY": 
            },
            "PASARELA_PAGOS_ENABLED": 
            },
            "PASARELA_PAGOS_PROVIDER": 
            },
        },
        # ============================================
        # CONFIGURACIÓN DE MONITOREO
        # ============================================
        "MONITOREO": 
            },
            "PROMETHEUS_ENABLED": 
            },
            "LOG_LEVEL": 
            },
        },
        # ============================================
        # CONFIGURACIÓN DE LA APLICACIÓN
        # ============================================
        "APLICACION": 
            },
            "VERSION_SISTEMA": 
            },
            "MANTENIMIENTO_PROGRAMADO": 
            },
            "MENSAJE_MANTENIMIENTO": 
            },
            "TIMEZONE": 
            },
        },

    @staticmethod
    def crear_configuraciones_default(db):
        """Crear configuraciones por defecto si no existen"""
        try:
            for 
            ) in ConfiguracionPorDefecto.CONFIGURACIONES_DEFAULT.items():
                for clave, config_data in configs.items():
                    # Verificar si ya existe
                    existing = 
                        db.query(ConfiguracionSistema)
                        .filter
                        .first()
                    if not existing:
                        # Crear nueva configuración
                        nueva_config = ConfiguracionSistema
                            valor=config_data.get("valor", ""),
                            valor_json=config_data.get("valor_json"),
                            descripcion=config_data.get("descripcion", ""),
                            tipo_dato=config_data.get("tipo_dato", "STRING"),
                            requerido=config_data.get("requerido", False),
                            visible_frontend=config_data.get
                            solo_lectura=config_data.get
                            opciones_validas=
                                json.dumps(config_data.get("opciones_validas"))
                                if config_data.get("opciones_validas")
                                else None
                            patron_validacion=config_data.get
                            valor_minimo=config_data.get("valor_minimo"),
                            valor_maximo=config_data.get("valor_maximo"),
                        db.add(nueva_config)
            db.commit()
            logger = logging.getLogger(__name__)
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
        smtp_user = ConfigHelper.get_config(db, "EMAIL", "SMTP_USERNAME")

    @staticmethod
    def is_whatsapp_enabled(db) -> bool:
        """Verificar si WhatsApp está habilitado"""
        return ConfigHelper.get_config

    @staticmethod
    def get_financial_config(db) -> Dict:
        """Obtener configuración financiera completa"""
        return 

    @staticmethod
    def get_notification_config(db) -> Dict:
        """Obtener configuración de notificaciones"""
        return 
