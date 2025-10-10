# backend/app/config.py
from pydantic_settings import BaseSettings
from typing import Optional, List
from functools import lru_cache
import os


class Settings(BaseSettings):
    """Configuración centralizada de la aplicación"""
    
    # ============================================
    # APLICACIÓN
    # ============================================
    APP_NAME: str = "Sistema de Préstamos y Cobranza"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    
    # ============================================
    # SERVIDOR
    # ============================================
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    
    # ============================================
    # BASE DE DATOS
    # ============================================
    DATABASE_URL: str
    
    # Pool de Conexiones (para producción)
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600
    DB_ECHO: bool = False  # SQL logging
    
    # ============================================
    # SEGURIDAD
    # ============================================
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    ALLOWED_ORIGINS: str = "*"  # En producción, usar dominios específicos
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Convierte ALLOWED_ORIGINS string a lista"""
        if self.ALLOWED_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    # ============================================
    # UVICORN (Servidor)
    # ============================================
    UVICORN_WORKERS: int = 1
    UVICORN_TIMEOUT_KEEP_ALIVE: int = 120
    UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN: int = 30
    
    # ============================================
    # LOGGING
    # ============================================
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "standard"  # "standard" o "json"
    
    # ============================================
    # HEALTH CHECK
    # ============================================
    HEALTH_CHECK_CACHE_DURATION: int = 30  # segundos
    
    # ============================================
    # BUILD
    # ============================================
    PYTHONUNBUFFERED: int = 1
    NIXPACKS_NO_CACHE: int = 0
    
    # ============================================
    # NOTIFICACIONES (Opcional)
    # ============================================
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: Optional[str] = None
    
    # ============================================
    # TWILIO (Opcional)
    # ============================================
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None
    
    # ============================================
    # MÉTODOS DE UTILIDAD
    # ============================================
    
    @property
    def is_production(self) -> bool:
        """Verifica si está en producción"""
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Verifica si está en desarrollo"""
        return self.ENVIRONMENT.lower() == "development"
    
    def get_database_url(self, hide_password: bool = False) -> str:
        """
        Retorna DATABASE_URL, opcionalmente ocultando password
        Útil para logging
        """
        if not hide_password:
            return self.DATABASE_URL
        
        # Ocultar password en logs
        if "@" in self.DATABASE_URL:
            parts = self.DATABASE_URL.split("@")
            user_part = parts[0].split("://")[1]
            if ":" in user_part:
                user = user_part.split(":")[0]
                return self.DATABASE_URL.replace(user_part, f"{user}:***")
        return self.DATABASE_URL
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = True
        extra = "allow"  # Permite variables extra sin error


@lru_cache()
def get_settings() -> Settings:
    """
    Obtiene configuración singleton (cache)
    Se carga una sola vez durante el ciclo de vida de la app
    """
    return Settings()


# Para importar fácilmente
settings = get_settings()
