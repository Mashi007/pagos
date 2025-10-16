# backend/app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
from functools import lru_cache


class Settings(BaseSettings):
    """Configuración centralizada de la aplicación"""
    
    # ============================================
    # APLICACIÓN
    # ============================================
    APP_NAME: str = "Sistema de Préstamos y Cobranza"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    
    # ============================================
    # SERVIDOR
    # ============================================
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    
    # ============================================
    # BASE DE DATOS
    # ============================================
    DATABASE_URL: str
    
    # Pool de Conexiones
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600
    DB_ECHO: bool = False
    
    # ============================================
    # SEGURIDAD Y AUTENTICACIÓN
    # ============================================
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # ============================================
    # USUARIO ADMINISTRADOR INICIAL
    # ============================================
    ADMIN_EMAIL: str = "itmaster@rapicreditca.com"
    ADMIN_PASSWORD: str = "R@pi_2025**"  # ⚠️ CAMBIAR EN PRODUCCIÓN: Usar variable de entorno ADMIN_PASSWORD
    
    # ============================================
    # VALIDACIÓN DE CONFIGURACIÓN
    # ============================================
    def validate_admin_credentials(self) -> bool:
        """Valida que las credenciales de admin estén configuradas correctamente"""
        if not self.ADMIN_EMAIL or not self.ADMIN_PASSWORD:
            return False
        if self.ADMIN_PASSWORD == "R@pi_2025**" and self.ENVIRONMENT == "production":
            raise ValueError("⚠️ CRÍTICO: Contraseña por defecto detectada en producción. Configure ADMIN_PASSWORD")
        return True
    
    # CORS
    ALLOWED_ORIGINS: str = "*"
    
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
    TASA_INTERES_BASE: float = 15.0
    TASA_MORA: float = 2.0
    TASA_MORA_DIARIA: float = 0.1
    
    MAX_CUOTA_PERCENTAGE: int = 40
    
    MONTO_MINIMO_PRESTAMO: float = 100.0
    MONTO_MAXIMO_PRESTAMO: float = 50000.0
    MIN_LOAN_AMOUNT: int = 1000000
    MAX_LOAN_AMOUNT: int = 50000000
    
    PLAZO_MINIMO_MESES: int = 1
    PLAZO_MAXIMO_MESES: int = 60
    MAX_LOAN_TERM: int = 60
    
    AMORTIZATION_METHODS: List[str] = ["FRANCES", "ALEMAN", "AMERICANO"]
    
    # ============================================
    # NOTIFICACIONES
    # ============================================
    DIAS_PREVIOS_RECORDATORIO: int = 3
    DIAS_MORA_ALERTA: int = 15
    
    # EMAIL
    EMAIL_ENABLED: bool = True
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    FROM_EMAIL: Optional[str] = "noreply@rapicredit.com"
    FROM_NAME: str = "RapiCredit"
    SMTP_FROM: Optional[str] = "noreply@rapicredit.com"
    SMTP_FROM_NAME: Optional[str] = "RapiCredit"
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False
    
    # WHATSAPP (Meta Developers API)
    WHATSAPP_ENABLED: bool = True
    WHATSAPP_API_URL: str = "https://graph.facebook.com/v18.0"
    WHATSAPP_ACCESS_TOKEN: Optional[str] = None
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = None
    WHATSAPP_BUSINESS_ACCOUNT_ID: Optional[str] = None
    WHATSAPP_WEBHOOK_VERIFY_TOKEN: Optional[str] = None
    
    # SMS - NO USADO (solo Email y WhatsApp vía Meta)
    # SMS_ENABLED: bool = False
    
    # ============================================
    # REPORTES
    # ============================================
    REPORTS_DIR: str = "/tmp/reports"
    REPORTS_CACHE_ENABLED: bool = True
    REPORTS_CACHE_TTL: int = 1800
    
    # ============================================
    # FILE UPLOADS
    # ============================================
    MAX_UPLOAD_SIZE: int = 10485760  # 10 MB
    ALLOWED_UPLOAD_EXTENSIONS: List[str] = [".pdf", ".jpg", ".jpeg", ".png", ".xlsx", ".xls"]
    UPLOAD_DIR: str = "/tmp/uploads"
    
    # ============================================
    # CONCILIACIÓN BANCARIA
    # ============================================
    TOLERANCIA_CONCILIACION: float = 0.50
    
    # ============================================
    # CACHE
    # ============================================
    REDIS_URL: Optional[str] = None
    CACHE_EXPIRE_SECONDS: int = 3600
    HEALTH_CHECK_CACHE_DURATION: int = 30
    
    # ============================================
    # PAGINACIÓN
    # ============================================
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 100
    
    # ============================================
    # LOGGING
    # ============================================
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "standard"
    
    # ============================================
    # SCHEDULER (Tareas Programadas)
    # ============================================
    ENABLE_SCHEDULER: bool = False
    SCHEDULER_TIMEZONE: str = "America/Asuncion"
    CRON_NOTIFY_VENCIMIENTOS: str = "0 8 * * *"
    CRON_CALCULAR_MORA: str = "0 1 * * *"
    CRON_BACKUP_DB: str = "0 3 * * *"
    
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
    # BUILD
    # ============================================
    PYTHONUNBUFFERED: int = 1
    NIXPACKS_NO_CACHE: int = 0
    
    # ============================================
    # UVICORN
    # ============================================
    UVICORN_WORKERS: int = 1
    UVICORN_TIMEOUT_KEEP_ALIVE: int = 120
    UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN: int = 30
    
    # ============================================
    # MÉTODOS DE UTILIDAD
    # ============================================
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() == "development"
    
    @property
    def is_staging(self) -> bool:
        return self.ENVIRONMENT.lower() == "staging"
    
    def get_database_url(self, hide_password: bool = False) -> str:
        """Retorna DATABASE_URL, opcionalmente ocultando password"""
        if not hide_password:
            return self.DATABASE_URL
        
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
    
    def validate_loan_amount(self, amount: float) -> bool:
        """Valida que el monto esté dentro de los límites"""
        return self.MONTO_MINIMO_PRESTAMO <= amount <= self.MONTO_MAXIMO_PRESTAMO
    
    def validate_loan_term(self, months: int) -> bool:
        """Valida que el plazo esté dentro de los límites"""
        return self.PLAZO_MINIMO_MESES <= months <= self.PLAZO_MAXIMO_MESES
    
    def calculate_max_cuota(self, ingreso_mensual: float) -> float:
        """Calcula la cuota máxima según el ingreso"""
        return (ingreso_mensual * self.MAX_CUOTA_PERCENTAGE) / 100
    
    # ✅ CRÍTICO: Usar model_config para Pydantic V2
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"  # Permite variables extra del .env
    )


@lru_cache()
def get_settings() -> Settings:
    """Obtiene configuración singleton (cache)"""
    return Settings()


# Instancia global
settings = get_settings()
