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
    ENVIRONMENT: str = "production"
    
    # Base de datos (opcional para el arranque inicial)
    DATABASE_URL: Optional[str] = None
    
    # Servidor
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    
    # CORS - más permisivo para Railway
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # JWT y Seguridad
    SECRET_KEY: str = "temporary-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # WhatsApp (opcional)
    WHATSAPP_API_TOKEN: Optional[str] = None
    WHATSAPP_PHONE_ID: Optional[str] = None
    WHATSAPP_BUSINESS_ID: Optional[str] = None
    VERIFY_TOKEN: Optional[str] = None
    
    # OpenAI (opcional)
    OPENAI_API_KEY: Optional[str] = None
    
    # Email (opcional)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: Optional[str] = None
    
    # Configuración de notificaciones
    NOTIFICACIONES_ACTIVAS: bool = False  # Desactivado por defecto
    DIAS_RECORDATORIO_PREVIO: List[int] = [3, 1]
    DIAS_RECORDATORIO_MORA: List[int] = [1, 3, 5]
    
    # Configuración de paginación
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        # No fallar si no existe .env
        env_file_encoding = "utf-8"

# Instancia global de configuración
settings = Settings()
