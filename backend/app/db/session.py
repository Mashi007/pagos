# backend/app/db/session.py
"""
SQLAlchemy configuration: Engine, SessionLocal and Base.
"""
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException
from app.core.config import settings

# CORRECTO: Importar desde app.core.config

# Constantes de configuración de pool
DEFAULT_POOL_SIZE = 5
DEFAULT_MAX_OVERFLOW = 10
DEFAULT_POOL_TIMEOUT = 30
DEFAULT_POOL_RECYCLE = 3600
DEFAULT_CONNECT_TIMEOUT = 30
DEFAULT_STATEMENT_TIMEOUT = 30000

# Configurar logger
logger = logging.getLogger(__name__)

# Crear engine de SQLAlchemy con configuración optimizada para producción
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Verifica conexión antes de usar
    pool_size=DEFAULT_POOL_SIZE,  # Conexiones permanentes
    max_overflow=DEFAULT_MAX_OVERFLOW,  # Conexiones adicionales
    pool_timeout=DEFAULT_POOL_TIMEOUT,  # Timeout de pool
    pool_recycle=DEFAULT_POOL_RECYCLE,  # Reciclar conexiones
    echo=settings.DB_ECHO,
    connect_args={
        "connect_timeout": DEFAULT_CONNECT_TIMEOUT,  # Timeout de conexión
        "application_name": "rapicredit_backend",
        "options": f"-c statement_timeout={DEFAULT_STATEMENT_TIMEOUT}"  # Timeout de queries
    }
)

# SessionLocal para crear sesiones de BD
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base para los modelos
Base = declarative_base()

# Dependency para FastAPI
def get_db():
    """
    Dependency que proporciona una sesión de base de datos.
    Se cierra automáticamente después de cada request.

    Si hay problemas de conexión, levanta HTTPException apropiada.
    """
    db = None
    try:
        # Crear sesión de base de datos
        db = SessionLocal()

        # Test básico de conexión (sin logging excesivo)
        db.execute(text("SELECT 1"))

        yield db

    except Exception as e:
        # Solo manejar errores reales de DB, no de autenticación

        # Verificar si es un error de autenticación HTTP
        error_str = str(e)
        auth_errors = ["401", "Not authenticated", "Email o contraseña incorrectos"]
        if any(auth_error in error_str for auth_error in auth_errors):
            # Re-lanzar errores de autenticación sin modificar
            raise e

        # CORRECCIÓN CRÍTICA: NO sobrescribir HTTPException que ya tienen mensajes específicos
        
        if isinstance(e, HTTPException):
            # Re-lanzar HTTPException sin modificar (preservar mensaje específico)
            raise e

        # Solo manejar errores reales de DB - usar logger estructurado
        logger.error(f"Error real de base de datos: {e}")
        logger.error(f"Tipo de error: {type(e).__name__}")

        # Solo para errores que NO son HTTPException
        raise HTTPException(
            status_code=503, 
            detail="Servicio de base de datos temporalmente no disponible"
        )
    finally:
        if db:
            try:
                db.close()
            except Exception:
                pass  # Ignorar errores al cerrar

def close_db_connections():
    """Cierra todas las conexiones de la pool al shutdown"""
    engine.dispose()
