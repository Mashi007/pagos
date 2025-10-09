import os
from typing import Optional
from functools import lru_cache


class Settings:
    """
    Configuración centralizada de la aplicación.
    Lee variables de entorno con validación y valores por defecto seguros.
    """
    
    def __init__(self):
        # ===== BASE DE DATOS =====
        self.DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
        
        # Validar que exista
        if not self.DATABASE_URL:
            raise ValueError(
                "❌ DATABASE_URL no está configurada. "
                "En Railway, asegúrate de vincular el servicio Postgres."
            )
        
        # Railway usa postgres://, SQLAlchemy necesita postgresql://
        if self.DATABASE_URL.startswith("postgres://"):
            self.DATABASE_URL = self.DATABASE_URL.replace(
                "postgres://", "postgresql://", 1
            )
        
        # Configuración de pool de conexiones
        self.DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))
        self.DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
        self.DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
        self.DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "3600"))
        
        # ===== ENTORNO =====
        self.ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
        self.DEBUG: bool = self.ENVIRONMENT == "development"
        
        # ===== SERVIDOR =====
        self.PORT: int = int(os.getenv("PORT", "8000"))
        self.HOST: str = os.getenv("HOST", "0.0.0.0")
        
        # ===== SEGURIDAD =====
        self.SECRET_KEY: str = os.getenv("SECRET_KEY", "")
        if not self.SECRET_KEY and self.ENVIRONMENT == "production":
            raise ValueError(
                "❌ SECRET_KEY es obligatoria en producción. "
                "Genera una con: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        
        # JWT
        self.JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", self.SECRET_KEY)
        self.JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
        self.ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
        )
        
        # CORS
        self.ALLOWED_ORIGINS: list = os.getenv(
            "ALLOWED_ORIGINS", 
            "*" if self.DEBUG else ""
        ).split(",")
        
        # ===== APLICACIÓN =====
        self.APP_NAME: str = os.getenv("APP_NAME", "Sistema de Pagos")
        self.APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
        self.API_PREFIX: str = os.getenv("API_PREFIX", "/api/v1")
        
        # ===== LOGGING =====
        self.LOG_LEVEL: str = os.getenv(
            "LOG_LEVEL", 
            "DEBUG" if self.DEBUG else "INFO"
        )
        
        # Imprimir configuración (sin datos sensibles)
        self._print_config()
    
    def _print_config(self):
        """Imprime la configuración cargada (sin exponer secretos)"""
        db_masked = self._mask_url(self.DATABASE_URL)
        
        print("\n" + "="*60)
        print(f"🚀 {self.APP_NAME} v{self.APP_VERSION}")
        print("="*60)
        print(f"🌍 Entorno: {self.ENVIRONMENT}")
        print(f"🔌 Puerto: {self.PORT}")
        print(f"🗄️  Base de datos: {db_masked}")
        print(f"🔐 SECRET_KEY: {'✅ Configurada' if self.SECRET_KEY else '❌ Falta'}")
        print(f"🔑 JWT: {'✅ Configurado' if self.JWT_SECRET_KEY else '❌ Falta'}")
        print(f"📝 Log level: {self.LOG_LEVEL}")
        print(f"🌐 CORS origins: {self.ALLOWED_ORIGINS}")
        print("="*60 + "\n")
    
    @staticmethod
    def _mask_url(url: str) -> str:
        """Enmascara la URL de la base de datos para logs seguros"""
        if not url:
            return "NO_CONFIGURADA"
        
        try:
            # postgresql://user:pass@host:5432/db -> postgresql://***:***@host:5432/db
            parts = url.split("@")
            if len(parts) == 2:
                protocol_and_creds = parts[0]
                host_and_db = parts[1]
                protocol = protocol_and_creds.split("//")[0]
                return f"{protocol}//***:***@{host_and_db}"
            return "***"
        except:
            return "***"


@lru_cache()
def get_settings() -> Settings:
    """
    Obtiene la configuración como singleton.
    @lru_cache asegura que solo se cree una instancia.
    """
    return Settings()


# Instancia global (para imports directos)
settings = get_settings()
