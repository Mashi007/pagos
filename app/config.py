from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    """
    Configuración de la aplicación usando Pydantic Settings
    """
    
    # Información general
    APP_NAME: str = "Sistema de Pagos y Cobranza"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    
    # Base de datos
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # Servidor
    PORT: int = int(os.getenv("PORT", 8000))
    HOST: str = "0.0.0.0"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://*.railway.app",
        os.getenv("FRONTEND_URL", "")
    ]
    
    # JWT y Seguridad
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 horas
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # WhatsApp (opcional)
    WHATSAPP_API_TOKEN: str = os.getenv("WHATSAPP_API_TOKEN", "")
    WHATSAPP_PHONE_ID: str = os.getenv("WHATSAPP_PHONE_ID", "")
    WHATSAPP_BUSINESS_ID: str = os.getenv("WHATSAPP_BUSINESS_ID", "")
    VERIFY_TOKEN: str = os.getenv("VERIFY_TOKEN", "")
    
    # OpenAI (opcional)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Email (opcional)
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "")
    
    # Configuración de notificaciones
    NOTIFICACIONES_ACTIVAS: bool = True
    DIAS_RECORDATORIO_PREVIO: List[int] = [3, 1]
    DIAS_RECORDATORIO_MORA: List[int] = [1, 3, 5]
    
    # Configuración de paginación
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Instancia global de configuración
settings = Settings()
