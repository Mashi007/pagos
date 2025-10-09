# app/config.py
from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    """
    Configuración de la aplicación usando Pydantic Settings
    """
    
    # Información general
    APP_NAME: str = "Sistema de Pagos y Cobranza"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    
    # Base de datos - Intenta múltiples variables
    DATABASE_URL: str = os.getenv("DATABASE_URL") or os.getenv("DATABASE_PUBLIC_URL") or ""
    
    # Servidor
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = "0.0.0.0"
    
    # CORS - más permisivo para Railway
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # JWT y Seguridad
    SECRET_KEY: str = os.getenv("SECRET_KEY", "temporary-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # WhatsApp (opcional)
    WHATSAPP_API_TOKEN: Optional[str] = os.getenv("WHATSAPP_API_TOKEN")
    WHATSAPP_PHONE_ID: Optional[str] = os.getenv("WHATSAPP_PHONE_ID")
    WHATSAPP_BUSINESS_ID: Optional[str] = os.getenv("WHATSAPP_BUSINESS_ID")
    VERIFY_TOKEN: Optional[str] = os.getenv("VERIFY_TOKEN")
    
    # OpenAI (opcional)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # Email (opcional)
    SMTP_HOST: Optional[str] = os.getenv("SMTP_HOST")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: Optional[str] = os.getenv("SMTP_USER")
    SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD")
    EMAIL_FROM: Optional[str] = os.getenv("EMAIL_FROM")
    
    # Configuración de notificaciones
    NOTIFICACIONES_ACTIVAS: bool = os.getenv("NOTIFICACIONES_ACTIVAS", "false").lower() == "true"
    DIAS_RECORDATORIO_PREVIO: List[int] = [3, 1]
    DIAS_RECORDATORIO_MORA: List[int] = [1, 3, 5]
    
    # Configuración de paginación
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        env_file_encoding = "utf-8"

# Instancia global de configuración
settings = Settings()
