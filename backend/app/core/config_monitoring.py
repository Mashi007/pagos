# backend/app/core/config_monitoring.py
"""
Configuración adicional para Monitoreo
Agregar estas variables a tu app/core/config.py existente
"""
from typing import Optional
from pydantic_settings import BaseSettings


class MonitoringSettings(BaseSettings):
    """
    Configuración de Monitoreo y Observabilidad
    Agregar estas variables a tu clase Settings principal
    """
    
    # ==========================================
    # SENTRY CONFIGURATION
    # ==========================================
    SENTRY_DSN: Optional[str] = None
    SENTRY_ENVIRONMENT: str = "production"
    SENTRY_TRACES_SAMPLE_RATE: float = 1.0  # 100% en dev, 0.1 en prod
    SENTRY_PROFILES_SAMPLE_RATE: float = 1.0
    
    # ==========================================
    # PROMETHEUS CONFIGURATION
    # ==========================================
    PROMETHEUS_ENABLED: bool = True
    PROMETHEUS_MULTIPROC_DIR: Optional[str] = None  # Para multi-worker
    
    # ==========================================
    # LOGGING CONFIGURATION
    # ==========================================
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FORMAT: str = "json"  # json o text
    
    # ==========================================
    # APPLICATION INFO
    # ==========================================
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "production"  # development, staging, production
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# ==========================================
# EJEMPLO DE INTEGRACIÓN EN config.py
# ==========================================
"""
En tu archivo app/core/config.py existente, agregar:

from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # ... tus configuraciones existentes ...
    
    # MONITOREO Y OBSERVABILIDAD
    SENTRY_DSN: Optional[str] = None
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1  # 10% en producción
    SENTRY_PROFILES_SAMPLE_RATE: float = 0.1
    PROMETHEUS_ENABLED: bool = True
    LOG_LEVEL: str = "INFO"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "production"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
"""

# ==========================================
# VARIABLES DE ENTORNO (.env)
# ==========================================
"""
# Monitoreo
SENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0
SENTRY_TRACES_SAMPLE_RATE=0.1
PROMETHEUS_ENABLED=true
LOG_LEVEL=INFO
ENVIRONMENT=production
APP_VERSION=1.0.0
"""
