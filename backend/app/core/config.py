# backend/app/core/config.py
"""
Configuración centralizada del sistema.
Todas las variables de entorno y settings.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Configuración de la aplicación"""
    
    # Aplicación
    APP_NAME: str = "Sistema de Préstamos y Cobranza"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    
    # Base de datos
    DATABASE_URL: str
    
    # Seguridad
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    ALLOWED_ORIGINS: str = "*"
    
    # Email (SMTP)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    FROM_EMAIL: Optional[str] = None
    FROM_NAME: str = "Sistema de Préstamos"
    
    # WhatsApp (Twilio)
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_WHATSAPP_NUMBER: Optional[str] = None
    
    # Reportes
    REPORTS_DIR: str = "/tmp/reports"
    
    # Paginación
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 100
    
    # Configuración de préstamos (valores por defecto)
    TASA_INTERES_BASE: float = 15.0  # %
    TASA_MORA: float = 2.0  # %
    MONTO_MINIMO_PRESTAMO: float = 100.0
    MONTO_MAXIMO_PRESTAMO: float = 50000.0
    PLAZO_MINIMO_MESES: int = 1
    PLAZO_MAXIMO_MESES: int = 60
    
    # Notificaciones
    DIAS_PREVIOS_RECORDATORIO: int = 3
    DIAS_MORA_ALERTA: int = 15
    
    # Conciliación bancaria
    TOLERANCIA_CONCILIACION: float = 0.50  # $0.50 de tolerancia
    
    # Cache
    REDIS_URL: Optional[str] = None
    CACHE_EXPIRE_SECONDS: int = 3600
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
