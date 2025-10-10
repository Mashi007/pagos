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
    API_PREFIX: str = "/api/v1"
    
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
    # SEGURIDAD Y AUTENTICACIÓN
    # ============================================
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    ALLOWED_ORIGINS: str = "*"  # En producción, usar dominios específicos
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Convierte ALLOWED_ORIGINS string a lista"""
        if self.ALLOWED_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # ============================================
    # AMORTIZACIÓN Y REGLAS DE NEGOCIO
    # ============================================
    # Tasa de mora diaria (%)
    TASA_MORA_DIARIA: float = 0.1
    
    # Porcentaje máximo de cuota vs ingreso mensual
    MAX_CUOTA_PERCENTAGE: int = 40
    
    # Montos mínimos y máximos de préstamo (Guaraníes)
    MIN_LOAN_AMOUNT: int = 1000000      # ₲1,000,000
    MAX_LOAN_AMOUNT: int = 50000000     # ₲50,000,000
    
    # Plazo máximo en meses
    MAX_LOAN_TERM: int = 60
    
    # Métodos de amortización permitidos
    AMORTIZATION_METHODS: List[str] = ["FRANCES", "ALEMAN", "AMERICANO"]
    
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
    # REPORTES
    # ============================================
    REPORTS_DIR: str = "/tmp/reports"
    REPORTS_CACHE_ENABLED: bool = True
    REPORTS_CACHE_TTL: int = 1800  # segundos (30 min)
    
    # ============================================
    # FILE UPLOADS
    # ============================================
    MAX_UPLOAD_SIZE: int = 10485760  # 10 MB
    ALLOWED_UPLOAD_EXTENSIONS: List[str] = [".pdf", ".jpg", ".jpeg", ".png", ".xlsx", ".xls"]
    UPLOAD_DIR: str = "/tmp/uploads"
    
    # ============================================
    # BUILD
    # ============================================
    PYTHONUNBUFFERED: int = 1
    NIXPACKS_NO_CACHE: int = 0
    
    # ============================================
    # NOTIFICACIONES - EMAIL (Opcional)
    # ============================================
    EMAIL_ENABLED: bool = False
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: Optional[str] = None
    SMTP_FROM_NAME: Optional[str] = "Sistema de Préstamos"
    
    # ============================================
    # NOTIFICACIONES - SMS/WHATSAPP (Twilio - Opcional)
    # ============================================
    SMS_ENABLED: bool = False
    WHATSAPP_ENABLED: bool = False
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None
    TWILIO_WHATSAPP_NUMBER: Optional[str] = None
    
    # ============================================
    # SCHEDULER (Tareas Programadas)
    # ============================================
    ENABLE_SCHEDULER: bool = False
    SCHEDULER_TIMEZONE: str = "America/Asuncion"
    
    # Cron expressions (si ENABLE_SCHEDULER=true)
    CRON_NOTIFY_VENCIMIENTOS: str = "0 8 * * *"   # 8 AM diario
    CRON_CALCULAR_MORA: str = "0 1 * * *"         # 1 AM diario
    CRON_BACKUP_DB: str = "0 3 * * *"             # 3 AM diario
    
    # ============================================
    # MONITOREO (Opcional)
    # ============================================
    SENTRY_DSN: Optional[str] = None
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1
    PROMETHEUS_ENABLED: bool = False
    
    # ============================================
    # FEATURE FLAGS
    # ============================================
    FEATURE_NOTIFICACIONES: bool = False
    FEATURE_REPORTES_PDF: bool = True
    FEATURE_DASHBOARD_KPIS: bool = True
    FEATURE_EXPORT_EXCEL: bool = True
    
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
    
    @property
    def is_staging(self) -> bool:
        """Verifica si está en staging"""
        return self.ENVIRONMENT.lower() == "staging"
    
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
            user_part = parts[0].split("://")
            if len(user_part) > 1:
                protocol = user_part[0]
                credentials = user_part[1]
                if ":" in credentials:
                    user = credentials.split(":")[0]
                    return f"{protocol}://{user}:***@{parts[1]}"
        return self.DATABASE_URL
    
    def validate_loan_amount(self, amount: int) -> bool:
        """Valida que el monto esté dentro de los límites"""
        return self.MIN_LOAN_AMOUNT <= amount <= self.MAX_LOAN_AMOUNT
    
    def validate_loan_term(self, months: int) -> bool:
        """Valida que el plazo esté dentro de los límites"""
        return 1 <= months <= self.MAX_LOAN_TERM
    
    def calculate_max_cuota(self, ingreso_mensual: float) -> float:
        """Calcula la cuota máxima según el ingreso"""
        return (ingreso_mensual * self.MAX_CUOTA_PERCENTAGE) / 100
    
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
