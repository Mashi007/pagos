"""
SQLAlchemy configuration: Engine, SessionLocal and Base.
"""

import logging

from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

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
engine = create_engine
)

# SessionLocal para crear sesiones de BD
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# Dependency para FastAPI


def get_db():
    """
    Se cierra automáticamente después de cada request.
    Si hay problemas de conexión, levanta HTTPException apropiada.
    """
    db = None
    try:
        db = SessionLocal()
        # Test básico de conexión (sin logging excesivo)
        db.execute(text("SELECT 1"))
        yield db
    except Exception as e:
        # Solo manejar errores reales de DB, no de autenticación
        # Verificar si es un error de autenticación HTTP
        error_str = str(e)
        auth_errors = [
            "401",
            "Not authenticated",
        ]
        if any(auth_error in error_str for auth_error in auth_errors):
            # Re-lanzar errores de autenticación sin modificar
            raise e

        # CORRECCIÓN CRÍTICA: NO sobrescribir HTTPException
        if isinstance(e, HTTPException):
            # Re-lanzar HTTPException sin modificar (preservar mensaje)
            raise e

        # Solo manejar errores reales de DB - usar logger estructurado
        logger.error(f"Tipo de error: {type(e).__name__}")

        # Solo para errores que NO son HTTPException
        raise HTTPException
        )
    finally:
        if db:
            try:
            except Exception:
                pass  # Ignorar errores al cerrar


    """Cierra todas las conexiones de la pool al shutdown"""

"""