"""
SQLAlchemy configuration: Engine, SessionLocal and Base.
"""

import logging
import os
from typing import Generator

from fastapi import HTTPException  # type: ignore[import-untyped]
from sqlalchemy import create_engine, text  # type: ignore[import-untyped]
from sqlalchemy.ext.declarative import declarative_base  # type: ignore[import-untyped]
from sqlalchemy.orm import sessionmaker  # type: ignore[import-untyped]

# Configuración de logging
logger = logging.getLogger(__name__)

# Configuración de la base de datos
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/pagos_db")

# Crear engine con configuración de encoding UTF-8
# Agregar parámetros de conexión para asegurar UTF-8
connect_args = {}
if DATABASE_URL.startswith("postgresql"):
    # Configurar codificación para psycopg2
    # Usar encoding 'latin1' como fallback si UTF-8 falla
    connect_args = {
        "client_encoding": "UTF8",
    }

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,  # 1 hora - reducir reciclaje innecesario
    pool_size=5,  # 5 conexiones permanentes
    max_overflow=10,  # 10 conexiones adicionales bajo carga
    pool_timeout=30,  # 30 segundos timeout para obtener conexión
    echo=False,
    connect_args=connect_args,
    # Manejar encoding de manera más robusta
    pool_reset_on_return="commit",
)

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
