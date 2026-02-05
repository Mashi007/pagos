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
    # Access token: duración en minutos. Override con ACCESS_TOKEN_EXPIRE_MINUTES en .env (ej. 240 = 4 horas).
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=240,
        description="Minutos hasta que expire el access token (default 4h). El refresh token sigue 7 días."
    )
    # Refresh token: duración en días (solo para renovar access token; no obliga a login hasta que expire).
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, description="Días hasta que expire el refresh token")

    # Usuario admin único (auth sin tabla users). Opcional.
    ADMIN_EMAIL: Optional[str] = Field(None, description="Email del usuario admin para login")
    ADMIN_PASSWORD: Optional[str] = Field(None, description="Contraseña del usuario admin para login")
    # Secreto para endpoint interno de restablecer contraseña (sincronizar usuario BD con ADMIN_PASSWORD).
    RESET_PASSWORD_SECRET: Optional[str] = Field(None, description="Secreto para POST /api/v1/auth/admin/reset-password (header X-Admin-Secret)")
    # Email al que se envía la notificación cuando un usuario solicita "Olvidé mi contraseña" (para envío de nueva).
    FORGOT_PASSWORD_NOTIFY_EMAIL: str = Field(
        default="itmaster@rapicreditca.com",
        description="Destino del correo de solicitud de restablecimiento de contraseña",
    )
    
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

    # URL para aviso cuando el webhook de WhatsApp falla (ej. Slack Incoming Webhook).
    # Si está configurada, se envía un POST con el mensaje de error.
    ALERT_WEBHOOK_URL: Optional[str] = Field(
        None,
        description="URL (ej. Slack Incoming Webhook) para alertas cuando falla el procesamiento del webhook de WhatsApp"
    )
    
    # ============================================
    # Email
    # ============================================
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    # Correo(s) para notificaciones de tickets CRM (varios separados por coma)
    TICKETS_NOTIFY_EMAIL: Optional[str] = Field(
        None,
        description="Email(s) para notificar cuando se crea o actualiza un ticket (separados por coma)"
    )
    
    # ============================================
    # AI / OpenRouter (clave solo en backend, nunca en frontend)
    # ============================================
    OPENROUTER_API_KEY: Optional[str] = Field(
        None,
        description="API Key de OpenRouter. Configurar en variables de entorno del dashboard (Render, etc.). Nunca se expone al frontend."
    )
    OPENROUTER_MODEL: Optional[str] = Field(
        default="openai/gpt-4o-mini",
        description="Modelo por defecto para chat/completions. Ej: openai/gpt-4o-mini, google/gemini-2.0-flash-001, anthropic/claude-3-5-haiku"
    )

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
    # Google OAuth (Drive/Sheets cuando no hay cuenta de servicio)
    # ============================================
    BACKEND_PUBLIC_URL: Optional[str] = Field(
        None,
        description="URL pública del backend para OAuth redirect_uri (ej. https://pagos-f2qf.onrender.com)"
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
        extra = "ignore"  # Ignorar variables extra del .env no definidas en Settings


# Instancia global de settings
settings = Settings()
