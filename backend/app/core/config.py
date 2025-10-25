# backend/app/core/config.py

from functools import lru_cache
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Constantes de configuración
DEFAULT_TOKEN_EXPIRE_MINUTES = 30
DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS = 7
DEFAULT_TASA_INTERES_BASE = 15.0
DEFAULT_TASA_MORA = 2.0
DEFAULT_TASA_MORA_DIARIA = 0.1
DEFAULT_MAX_CUOTA_PERCENTAGE = 40
DEFAULT_MONTO_MINIMO_PRESTAMO = 100.0
DEFAULT_MONTO_MAXIMO_PRESTAMO = 50000.0
DEFAULT_MIN_LOAN_AMOUNT = 1000000
DEFAULT_MAX_LOAN_AMOUNT = 50000000
DEFAULT_PLAZO_MINIMO_MESES = 1
DEFAULT_PLAZO_MAXIMO_MESES = 60
DEFAULT_MAX_LOAN_TERM = 60
DEFAULT_DIAS_PREVIOS_RECORDATORIO = 3
DEFAULT_DIAS_MORA_ALERTA = 15
DEFAULT_SMTP_PORT = 587
DEFAULT_MAX_UPLOAD_SIZE = 10485760
DEFAULT_TOLERANCIA_CONCILIACION = 0.50
DEFAULT_CACHE_EXPIRE_SECONDS = 3600
DEFAULT_HEALTH_CHECK_CACHE_DURATION = 30
DEFAULT_PAGE_SIZE = 50
DEFAULT_MAX_PAGE_SIZE = 100
DEFAULT_SENTRY_TRACES_SAMPLE_RATE = 0.1
DEFAULT_UVICORN_WORKERS = 1
DEFAULT_UVICORN_TIMEOUT_KEEP_ALIVE = 120
DEFAULT_UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN = 30


class Settings(BaseSettings):
    """Configuración centralizada de la aplicación"""

    # ============================================
    # APLICACIÓN
    # ============================================
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # ============================================
    # SERVIDOR
    # ============================================
    HOST: str = "0.0.0.0"
    PORT: int = 8080

    # ============================================
    # ============================================
    CORS_ORIGINS: List[str] = [
        "https://rapicredit.onrender.com",  # ✅ Frontend en Render
        "null",  # ✅ Para requests sin origin (scripts, herramientas)
        "*",  # ✅ Temporalmente permisivo para debugging
    ]

    # ============================================
    # BASE DE DATOS
    # ============================================
    DATABASE_URL: str

    # Pool de Conexiones
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600
    DB_ECHO: bool = False

    # ============================================
    # SEGURIDAD Y AUTENTICACIÓN
    # ============================================
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = DEFAULT_TOKEN_EXPIRE_MINUTES
    REFRESH_TOKEN_EXPIRE_DAYS: int = DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS

    # ============================================
    # USUARIO ADMINISTRADOR INICIAL
    # ============================================
    ADMIN_EMAIL: str = "itmaster@rapicreditca.com"
    ADMIN_PASSWORD: str = Field(
        default="R@pi_2025**", env="ADMIN_PASSWORD"
    )  # ✅ Variable de entorno

    # ============================================
    # VALIDACIÓN DE CONFIGURACIÓN
    # ============================================


    def validate_admin_credentials(self) -> bool:
        """Valida que las credenciales de admin estén configuradas"""
        if not self.ADMIN_EMAIL or not self.ADMIN_PASSWORD:
            return False
        if (
            self.ADMIN_PASSWORD == "R@pi_2025**"
            and self.ENVIRONMENT == "production"
        ):
            raise ValueError(
                "⚠️ CRÍTICO: Contraseña por defecto detectada en producción. "
                "Configure ADMIN_PASSWORD"
            )
        return True


    def validate_cors_origins(self) -> bool:
        """Valida que CORS no esté abierto en producción"""
        if self.ENVIRONMENT == "production" and "*" in self.CORS_ORIGINS:
            raise ValueError(
                "⚠️ CRÍTICO: CORS con wildcard (*) detectado en producción. "
                "CORS_ORIGINS='[\"https://tu-dominio.com\"]'"
            )
        return True

    # ============================================
    # AMORTIZACIÓN Y REGLAS DE NEGOCIO
    # ============================================
    TASA_INTERES_BASE: float = DEFAULT_TASA_INTERES_BASE
    TASA_MORA: float = DEFAULT_TASA_MORA
    TASA_MORA_DIARIA: float = DEFAULT_TASA_MORA_DIARIA
    MAX_CUOTA_PERCENTAGE: int = DEFAULT_MAX_CUOTA_PERCENTAGE
    MONTO_MINIMO_PRESTAMO: float = DEFAULT_MONTO_MINIMO_PRESTAMO
    MONTO_MAXIMO_PRESTAMO: float = DEFAULT_MONTO_MAXIMO_PRESTAMO
    MIN_LOAN_AMOUNT: int = DEFAULT_MIN_LOAN_AMOUNT
    MAX_LOAN_AMOUNT: int = DEFAULT_MAX_LOAN_AMOUNT
    PLAZO_MINIMO_MESES: int = DEFAULT_PLAZO_MINIMO_MESES
    PLAZO_MAXIMO_MESES: int = DEFAULT_PLAZO_MAXIMO_MESES
    MAX_LOAN_TERM: int = DEFAULT_MAX_LOAN_TERM
    AMORTIZATION_METHODS: List[str] = ["FRANCES", "ALEMAN", "AMERICANO"]

    # ============================================
    # NOTIFICACIONES
    # ============================================
    DIAS_PREVIOS_RECORDATORIO: int = DEFAULT_DIAS_PREVIOS_RECORDATORIO
    DIAS_MORA_ALERTA: int = DEFAULT_DIAS_MORA_ALERTA

    # EMAIL
    EMAIL_ENABLED: bool = True
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = DEFAULT_SMTP_PORT
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    FROM_EMAIL: Optional[str] = "noreply@rapicredit.com"
    FROM_NAME: str = "RapiCredit"
    SMTP_FROM: Optional[str] = "noreply@rapicredit.com"
    SMTP_FROM_NAME: Optional[str] = "RapiCredit"
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False

    # WHATSAPP (Meta Developers API)
    WHATSAPP_ENABLED: bool = True
    WHATSAPP_API_URL: str = "https://graph.facebook.com/v18.0"
    WHATSAPP_ACCESS_TOKEN: Optional[str] = None
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = None
    WHATSAPP_BUSINESS_ACCOUNT_ID: Optional[str] = None
    WHATSAPP_WEBHOOK_VERIFY_TOKEN: Optional[str] = None

    # SMS - NO USADO (solo Email y WhatsApp vía Meta)
    # SMS_ENABLED: bool = False

    # ============================================
    # REPORTES
    # ============================================
    REPORTS_DIR: str = "/tmp/reports"
    REPORTS_CACHE_ENABLED: bool = True
    REPORTS_CACHE_TTL: int = 1800

    # ============================================
    # FILE UPLOADS
    # ============================================
    MAX_UPLOAD_SIZE: int = DEFAULT_MAX_UPLOAD_SIZE  # 10 MB
    ALLOWED_UPLOAD_EXTENSIONS: List[str] = [
        ".pd",
        ".jpg",
        ".jpeg",
        ".png",
        ".xlsx",
        ".xls",
    ]
    UPLOAD_DIR: str = "/tmp/uploads"

    # ============================================
    # CONCILIACIÓN BANCARIA
    # ============================================
    TOLERANCIA_CONCILIACION: float = DEFAULT_TOLERANCIA_CONCILIACION

    # ============================================
    # CACHE
    # ============================================
    REDIS_URL: Optional[str] = None
    CACHE_EXPIRE_SECONDS: int = DEFAULT_CACHE_EXPIRE_SECONDS
    HEALTH_CHECK_CACHE_DURATION: int = DEFAULT_HEALTH_CHECK_CACHE_DURATION

    # ============================================
    # PAGINACIÓN
    # ============================================
    DEFAULT_PAGE_SIZE: int = DEFAULT_PAGE_SIZE
    MAX_PAGE_SIZE: int = DEFAULT_MAX_PAGE_SIZE

    # ============================================
    # LOGGING
    # ============================================
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "standard"

    # ============================================
    # SCHEDULER (Tareas Programadas)
    # ============================================
    ENABLE_SCHEDULER: bool = False
    SCHEDULER_TIMEZONE: str = "America/Asuncion"
    CRON_NOTIFY_VENCIMIENTOS: str = "0 8 * * *"
    CRON_CALCULAR_MORA: str = "0 1 * * *"
    CRON_BACKUP_DB: str = "0 3 * * *"

    # ============================================
    # MONITOREO (Opcional)
    # ============================================
    SENTRY_DSN: Optional[str] = None
    SENTRY_TRACES_SAMPLE_RATE: float = DEFAULT_SENTRY_TRACES_SAMPLE_RATE
    PROMETHEUS_ENABLED: bool = False

    # ============================================
    # FEATURE FLAGS
    # ============================================
    FEATURE_NOTIFICACIONES: bool = False
    FEATURE_REPORTES_PDF: bool = True
    FEATURE_DASHBOARD_KPIS: bool = True
    FEATURE_EXPORT_EXCEL: bool = True

    # ============================================
    # BUILD
    # ============================================
    PYTHONUNBUFFERED: int = 1
    NIXPACKS_NO_CACHE: int = 0

    # ============================================
    # UVICORN
    # ============================================
    UVICORN_WORKERS: int = DEFAULT_UVICORN_WORKERS
    UVICORN_TIMEOUT_KEEP_ALIVE: int = DEFAULT_UVICORN_TIMEOUT_KEEP_ALIVE
    UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN: int = (
        DEFAULT_UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN
    )

    # ============================================
    # MÉTODOS DE UTILIDAD
    # ============================================
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() == "development"

    @property
    def is_staging(self) -> bool:
        return self.ENVIRONMENT.lower() == "staging"


    def get_database_url(self, hide_password: bool = False) -> str:
        """Retorna DATABASE_URL, opcionalmente ocultando password"""
        if not hide_password:
            return self.DATABASE_URL

        if "@" in self.DATABASE_URL:
            parts = self.DATABASE_URL.split("@")
            user_part = parts[0].split("://")
            if len(user_part) > 1:
                protocol = user_part[0]
                credentials = user_part[1]
                if ":" in credentials:
                    user = credentials.split(":")[0]
                    return f"{protocol}://{user}:***@{parts[1]}"

        return self.DATABASE_URL


    def validate_loan_amount(self, amount: float) -> bool:
        return (
            self.MONTO_MINIMO_PRESTAMO <= amount <= self.MONTO_MAXIMO_PRESTAMO
        )


    def validate_loan_term(self, months: int) -> bool:
        return self.PLAZO_MINIMO_MESES <= months <= self.PLAZO_MAXIMO_MESES


    def calculate_max_cuota(self, ingreso_mensual: float) -> float:
        """Calcula la cuota máxima según el ingreso"""
        return (ingreso_mensual * self.MAX_CUOTA_PERCENTAGE) / 100

    # ✅ CRÍTICO: Usar model_config para Pydantic V2
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow",  # Permite variables extra del .env
    )

@lru_cache()
def get_settings() -> Settings:
    """Obtiene configuración singleton (cache)"""
    return Settings()

# Instancia global
settings = get_settings()
