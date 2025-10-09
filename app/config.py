# app/config.py
import os
from typing import Optional

class Settings:
    """Configuración centralizada de la aplicación"""
    
    # Base de datos
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # Entorno
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    
    # Aplicación
    PROJECT_NAME: str = "Sistema de Pagos"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Puerto
    PORT: int = int(os.getenv("PORT", 8000))
    
    # CORS
    BACKEND_CORS_ORIGINS: list = ["*"]
    
    def __init__(self):
        if not self.DATABASE_URL:
            raise ValueError("❌ DATABASE_URL no está configurada")

# Instancia global
settings = Settings()
