# app/config.py
import os
from typing import List, Optional
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


class Settings:
    """Configuración centralizada de la aplicación"""
    
    def __init__(self):
        # Base de datos - CRÍTICO
        self.DATABASE_URL: str = os.getenv("DATABASE_URL", "")
        
        if not self.DATABASE_URL:
            logger.warning("⚠️  DATABASE_URL no configurada.")
        else:
            if self.DATABASE_URL.startswith("postgres://"):
                self.DATABASE_URL = self.DATABASE_URL.replace("postgres://", "postgresql://", 1)
                logger.info("🔧 DATABASE_URL normalizada: postgres:// → postgresql://")
        
        # Aplicación
        self.APP_NAME: str = os.getenv("APP_NAME", "Sistema de Préstamos y Cobranza")
        self.APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
        self.ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
        self.DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
        
        # ✅ NUEVO: Forzar recreación de tablas
        self.FORCE_RECREATE_TABLES: bool = os.getenv("FORCE_RECREATE_TABLES", "true").lower() == "true"
        
        # API
        self.API_PREFIX: str = os.getenv("API_PREFIX", "/api/v1")
        
        # CORS
        origins = os.getenv("ALLOWED_ORIGINS", "")
        self.ALLOWED_ORIGINS: List[str] = [
            origin.strip() 
            for origin in origins.split(",") 
            if origin.strip()
        ] if origins else ["*"]
        
        # Puerto
        self.PORT: int = int(os.getenv("PORT", "8080"))
        
        # Logging
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
        
        # JWT
        self.SECRET_KEY: str = os.getenv("SECRET_KEY", "")
        self.ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
        self.ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
        )


_settings_instance: Optional[Settings] = None


@lru_cache()
def get_settings() -> Settings:
    return Settings()


def settings() -> Settings:
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = get_settings()
    return _settings_instance
