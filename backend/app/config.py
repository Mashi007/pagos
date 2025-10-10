# app/config.py
import os
from typing import List, Optional
from functools import lru_cache

class Settings:
    """Configuración centralizada de la aplicación"""
    
    def __init__(self):
        # Base de datos - CRÍTICO
        self.DATABASE_URL: str = os.getenv("DATABASE_URL", "")
        if not self.DATABASE_URL:
            raise ValueError(
                "❌ DATABASE_URL no está configurada. "
                "En Railway, asegúrate de vincular el servicio Postgres."
            )
        
        # Aplicación
        self.APP_NAME: str = os.getenv("APP_NAME", "Sistema de Pagos")
        self.APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
        self.ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
        self.DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
        
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
        self.PORT: int = int(os.getenv("PORT", "8000"))
        
        # Logging
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
        
        # JWT
        self.SECRET_KEY: str = os.getenv("SECRET_KEY", "")
        self.ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
        self.ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
        )
    
    def display_config(self):
        """Muestra la configuración (sin datos sensibles)"""
        db_display = self.DATABASE_URL.split('@')[1] if '@' in self.DATABASE_URL else '***'
        secret_display = "✅ Configurada" if self.SECRET_KEY else "⚠️  No configurada"
        
        print("\n" + "="*60)
        print(f"🚀 {self.APP_NAME} v{self.APP_VERSION}")
        print("="*60)
        print(f"🌍 Entorno: {self.ENVIRONMENT}")
        print(f"🔌 Puerto: {self.PORT}")
        print(f"🗄️  Base de datos: postgresql://***:***@{db_display}")
        print(f"🔐 SECRET_KEY: {secret_display}")
        print(f"🔑 JWT: {'✅ Configurado' if self.SECRET_KEY else '⚠️  Pendiente'}")
        print(f"📝 Log level: {self.LOG_LEVEL}")
        print(f"🌐 CORS origins: {self.ALLOWED_ORIGINS}")
        print("="*60 + "\n")


# Variable global para caché manual
_settings_instance: Optional[Settings] = None


@lru_cache()
def get_settings() -> Settings:
    """
    Factory cacheada para obtener instancia de Settings.
    Solo se ejecuta cuando realmente se necesita.
    """
    return Settings()


def settings() -> Settings:
    """
    Función helper para compatibilidad con código existente.
    Permite usar: from app.config import settings
    """
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = get_settings()
    return _settings_instance


# IMPORTANTE: NO instanciar aquí para evitar errores en import-time
# Los archivos que usen settings deben llamar get_settings() o settings()
