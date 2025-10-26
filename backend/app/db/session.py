"""
SQLAlchemy configuration: Engine, SessionLocal and Base.
"""

import logging
import os
from typing import Generator

from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Configuración de logging
logger = logging.getLogger(__name__)

# Configuración de la base de datos
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/pagos_db")

# Crear engine
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=300, echo=False)

# Crear SessionLocal
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Crear Base para modelos
Base = declarative_base()


def get_db() -> Generator:
    """
    Dependency para obtener sesión de base de datos.
    Se cierra automáticamente después de cada request.
    Si hay problemas de conexión, levanta HTTPException apropiada.
    """
    db = None
    try:
        db = SessionLocal()
        # Test básico de conexión
        db.execute(text("SELECT 1"))
        yield db
    except Exception as e:
        # Verificar si es un error de autenticación HTTP
        error_str = str(e)
        auth_errors = ["401", "Not authenticated", "Unauthorized"]

        if any(auth_error in error_str for auth_error in auth_errors):
            # Re-lanzar errores de autenticación sin modificar
            raise e

        # NO sobrescribir HTTPException
        if isinstance(e, HTTPException):
            # Re-lanzar HTTPException sin modificar (preservar mensaje)
            raise e

        # Solo manejar errores reales de DB
        logger.error(f"Error de base de datos: {type(e).__name__}: {str(e)}")

        # Crear HTTPException para errores de DB
        raise HTTPException(status_code=500, detail="Error de conexión a la base de datos")
    finally:
        if db:
            try:
                db.close()
            except Exception:
                pass  # Ignorar errores al cerrar


def close_db_connections():
    """Cierra todas las conexiones de la pool al shutdown"""
    global engine
    if engine:
        engine.dispose()
        engine = None


def test_connection() -> bool:
    """
    Prueba la conexión a la base de datos

    Returns:
        True si la conexión es exitosa, False en caso contrario
    """
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except Exception as e:
        logger.error(f"Error probando conexión: {e}")
        return False
