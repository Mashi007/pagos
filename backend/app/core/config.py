"""
Configuración del sistema usando Pydantic Settings
"""
import json
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Configuración de la aplicación"""
    
    # ============================================
    # Configuración General
    # ============================================
    PROJECT_NAME: str = "Sistema de Pagos"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    
    # ============================================
    # Base de Datos
    # ============================================
    DATABASE_URL: str = Field(
        ...,
        description="URL de conexión a PostgreSQL"
    )
    
    # ============================================
    # Seguridad
    # ============================================
    SECRET_KEY: str = Field(
        ...,
        description="Clave secreta para JWT"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Usuario admin único (auth sin tabla users). Opcional.
    ADMIN_EMAIL: Optional[str] = Field(None, description="Email del usuario admin para login")
    ADMIN_PASSWORD: Optional[str] = Field(None, description="Contraseña del usuario admin para login")
    
    @validator('SECRET_KEY')
    def validate_secret_key(cls, v):
        """Validar que SECRET_KEY tenga longitud y complejidad adecuadas"""
        if len(v) < 32:
            raise ValueError('SECRET_KEY debe tener al menos 32 caracteres para seguridad adecuada')
        # Validar que no sea un valor común o débil
        weak_keys = ['secret', 'password', '123456', 'admin', 'test', 'dev', 'development']
        if v.lower() in weak_keys or len(set(v)) < 8:
            raise ValueError('SECRET_KEY debe ser una cadena aleatoria y segura, no un valor común')
        return v
    
    # ============================================
    # WhatsApp / Meta API
    # ============================================
    WHATSAPP_VERIFY_TOKEN: Optional[str] = Field(
        None,
        description="Token de verificación del webhook de WhatsApp (Meta)"
    )
    WHATSAPP_ACCESS_TOKEN: Optional[str] = Field(
        None,
        description="Access Token de WhatsApp Business API (Meta)"
    )
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = Field(
        None,
        description="Phone Number ID de WhatsApp Business"
    )
    WHATSAPP_BUSINESS_ACCOUNT_ID: Optional[str] = Field(
        None,
        description="Business Account ID de WhatsApp"
    )
    WHATSAPP_APP_SECRET: Optional[str] = Field(
        None,
        description="App Secret de Meta para verificar firma de webhooks (recomendado)"
    )
    
    # ============================================
    # Email
    # ============================================
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    
    # ============================================
    # Redis (Cache)
    # ============================================
    REDIS_URL: Optional[str] = Field(
        None,
        description="URL de conexión a Redis (opcional)"
    )
    
    # ============================================
    # Sentry (Monitoreo)
    # ============================================
    SENTRY_DSN: Optional[str] = Field(
        None,
        description="DSN de Sentry para monitoreo (opcional)"
    )
    
    # ============================================
    # CORS
    # ============================================
    CORS_ORIGINS: Optional[str] = Field(
        default='["http://localhost:3000", "http://localhost:5173", "https://pagos-f2qf.onrender.com", "https://rapicredit.onrender.com"]',
        description="Lista de orígenes permitidos para CORS (formato JSON o separado por comas). Incluye desarrollo y producción."
    )
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Retorna CORS_ORIGINS como lista"""
        if not self.CORS_ORIGINS or self.CORS_ORIGINS.strip() == '':
            return ["http://localhost:3000", "http://localhost:5173", "https://pagos-f2qf.onrender.com", "https://rapicredit.onrender.com"]
        
        # Intentar parsear como JSON
        try:
            parsed = json.loads(self.CORS_ORIGINS)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass
        
        # Si no es JSON válido, tratar como string separado por comas
        return [origin.strip() for origin in self.CORS_ORIGINS.split(',') if origin.strip()]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Instancia global de settings
settings = Settings()
