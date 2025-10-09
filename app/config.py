# app/config.py
from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    """Configuración centralizada de la aplicación"""
    
    # Información general
    APP_NAME: str = "Sistema de Pagos y Cobranza"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    
    # Base de datos
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # Servidor
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = "0.0.0.0"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # JWT y Seguridad
    SECRET_KEY: str = os.getenv("SECRET_KEY", "CHANGE-IN-PRODUCTION")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 horas
    
    # Configuración de paginación
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    def validate_critical_config(self) -> bool:
        """Valida configuración crítica"""
        if not self.DATABASE_URL:
            raise ValueError("❌ DATABASE_URL no configurada")
        return True
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Instancia global
settings = Settings()

# Validar al importar
try:
    settings.validate_critical_config()
    print(f"✅ Configuración cargada: {settings.ENVIRONMENT}")
except ValueError as e:
    print(f"⚠️ {e}")
