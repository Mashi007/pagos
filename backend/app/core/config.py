"""
Configuración de la aplicación
"""

from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Configuración de la aplicación usando Pydantic BaseSettings
    """

    # ============================================
    # CONFIGURACIÓN BÁSICA
    # ============================================
    APP_NAME: str = "RapiCredit API"
    APP_VERSION: str = "1.0.0"
    DESCRIPTION: str = "API para sistema de préstamos RapiCredit"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")

    # ============================================
    # BASE DE DATOS
    # ============================================
    DATABASE_URL: str = Field(
        default="postgresql://user:password@localhost/pagos_db", env="DATABASE_URL"
    )

    # ============================================
    # SEGURIDAD
    # ============================================
    SECRET_KEY: str = Field(
        default="your-secret-key-here-change-in-production", env="SECRET_KEY"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ============================================
    # CORS
    # ============================================
    CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:5173",
            "https://rapicredit.onrender.com",  # Frontend en producción
        ],
        env="CORS_ORIGINS",
    )
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    # ============================================
    # USUARIO ADMINISTRADOR INICIAL
    # ============================================
    ADMIN_EMAIL: str = "itmaster@rapicreditca.com"
    ADMIN_PASSWORD: str = Field(default="R@pi_2025**", env="ADMIN_PASSWORD")

    # ============================================
    # AMORTIZACIÓN Y REGLAS DE NEGOCIO
    # ============================================
    TASA_INTERES_BASE: float = 12.0  # 12% anual
    TASA_MORA: float = 2.0  # 2% mensual
    TASA_MORA_DIARIA: float = 0.067  # 2% / 30 días
    MAX_CUOTA_PERCENTAGE: int = 40  # Máximo 40% del ingreso
    MONTO_MINIMO_PRESTAMO: float = 1000.0
    MONTO_MAXIMO_PRESTAMO: float = 50000.0
    PLAZO_MINIMO_MESES: int = 6
    PLAZO_MAXIMO_MESES: int = 36

    # ============================================
    # NOTIFICACIONES
    # ============================================
    DIAS_PREVIOS_RECORDATORIO: int = 3
    DIAS_MORA_ALERTA: int = 5

    # EMAIL
    EMAIL_ENABLED: bool = True
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    FROM_EMAIL: Optional[str] = "noreply@rapicredit.com"
    FROM_NAME: str = "RapiCredit"
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False

    # WHATSAPP (Meta Developers API)
    WHATSAPP_ENABLED: bool = True
    WHATSAPP_API_URL: str = "https://graph.facebook.com/v18.0"
    WHATSAPP_ACCESS_TOKEN: Optional[str] = None
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = None
    WHATSAPP_BUSINESS_ACCOUNT_ID: Optional[str] = None
    WHATSAPP_WEBHOOK_VERIFY_TOKEN: Optional[str] = None

    # ============================================
    # REPORTES
    # ============================================
    REPORTS_DIR: str = "/tmp/reports"
    REPORTS_CACHE_ENABLED: bool = True
    REPORTS_CACHE_TTL: int = 1800

    # ============================================
    # FILE UPLOADS
    # ============================================
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_UPLOAD_EXTENSIONS: List[str] = [
        ".pdf",
        ".jpg",
        ".jpeg",
        ".png",
        ".xlsx",
        ".xls",
        ".doc",
        ".docx",
    ]
    UPLOAD_DIR: str = "uploads"

    # ============================================
    # LOGGING
    # ============================================
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # ============================================
    # VALIDACIÓN DE CONFIGURACIÓN
    # ============================================

    def validate_admin_credentials(self) -> bool:
        """Valida que las credenciales de admin estén configuradas"""
        if not self.ADMIN_EMAIL or not self.ADMIN_PASSWORD:
            return False
        if len(self.ADMIN_PASSWORD) < 6:
            raise ValueError("La contraseña de admin debe tener al menos 6 caracteres")
        return True

    def validate_cors_origins(self) -> bool:
        """Valida que CORS no esté abierto en producción"""
        if self.ENVIRONMENT == "production" and "*" in self.CORS_ORIGINS:
            raise ValueError(
                "CRÍTICO: CORS con wildcard (*) detectado en producción. "
                "CORS_ORIGINS debe especificar dominios específicos"
            )
        return True

    def validate_database_url(self) -> bool:
        """Valida que la URL de base de datos sea válida"""
        if (
            not self.DATABASE_URL
            or self.DATABASE_URL == "postgresql://user:password@localhost/pagos_db"
        ):
            if self.ENVIRONMENT == "production":
                raise ValueError("DATABASE_URL debe estar configurada en producción")
        return True

    def validate_all(self) -> bool:
        """Valida toda la configuración"""
        self.validate_admin_credentials()
        self.validate_cors_origins()
        self.validate_database_url()
        return True

    class Config:
        env_file = ".env"
        case_sensitive = True


# Instancia global de configuración
settings = Settings()

# Validar configuración al importar
try:
    settings.validate_all()
except ValueError as e:
    print(f"Error de configuración: {e}")
    if settings.ENVIRONMENT == "production":
        raise
