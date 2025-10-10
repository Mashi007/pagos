# app/config.py
import os
from typing import List

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

    def display_config(self):
        """Muestra la configuración (sin datos sensibles)"""
        print("\n" + "="*60)
        print(f"🚀 {self.APP_NAME} v{self.APP_VERSION}")
        print("="*60)
        print(f"🌍 Entorno: {self.ENVIRONMENT}")
        print(f"🔌 Puerto: {self.PORT}")
        print(f"🗄️  Base de datos: {self.DATABASE_URL.split('@')[1] if '@' in self.DATABASE_URL else 'configurada'}")
        print(f"📝 Log level: {self.LOG_LEVEL}")
        print(f"🌐 CORS origins: {self.ALLOWED_ORIGINS}")
        print("="*60 + "\n")


def get_settings() -> Settings:
    """Factory para obtener instancia de Settings"""
    return Settings()


# ⚠️ NO crear instancia global aquí
# settings = Settings()  # ❌ ELIMINAR ESTA LÍNEA
