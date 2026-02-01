"""
Configuración del sistema usando Pydantic Settings
"""
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Configuración de la aplicación"""
    
    # ============================================
    # Configuración General
    # ============================================
    PROJECT_NAME: str = "Sistema de Pagos"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    
    # ============================================
    # Base de Datos
    # ============================================
    DATABASE_URL: str = Field(
        ...,
        description="URL de conexión a PostgreSQL"
    )
    
    # ============================================
    # Seguridad
    # ============================================
    SECRET_KEY: str = Field(
        ...,
        description="Clave secreta para JWT"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # ============================================
    # WhatsApp / Meta API
    # ============================================
    WHATSAPP_VERIFY_TOKEN: Optional[str] = Field(
        None,
        description="Token de verificación del webhook de WhatsApp (Meta)"
    )
    WHATSAPP_ACCESS_TOKEN: Optional[str] = Field(
        None,
        description="Access Token de WhatsApp Business API (Meta)"
    )
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = Field(
        None,
        description="Phone Number ID de WhatsApp Business"
    )
    WHATSAPP_BUSINESS_ACCOUNT_ID: Optional[str] = Field(
        None,
        description="Business Account ID de WhatsApp"
    )
    
    # ============================================
    # Email
    # ============================================
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    
    # ============================================
    # Redis (Cache)
    # ============================================
    REDIS_URL: Optional[str] = Field(
        None,
        description="URL de conexión a Redis (opcional)"
    )
    
    # ============================================
    # Sentry (Monitoreo)
    # ============================================
    SENTRY_DSN: Optional[str] = Field(
        None,
        description="DSN de Sentry para monitoreo (opcional)"
    )
    
    # ============================================
    # CORS
    # ============================================
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Instancia global de settings
settings = Settings()
