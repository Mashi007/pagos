"""
SQLAlchemy configuration: Engine, SessionLocal and Base.
"""

import logging
import os
from typing import Generator

from fastapi import HTTPException, RequestValidationError  # type: ignore[import-untyped]
from sqlalchemy import create_engine, text  # type: ignore[import-untyped]
from sqlalchemy.ext.declarative import declarative_base  # type: ignore[import-untyped]
from sqlalchemy.orm import sessionmaker  # type: ignore[import-untyped]

# Configuración de logging
logger = logging.getLogger(__name__)

# Configuración de la base de datos
# ✅ CORRECCIÓN: Manejar encoding de DATABASE_URL correctamente
database_url_raw = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/pagos_db")
if database_url_raw:
    # Si la URL tiene caracteres especiales, codificarlos correctamente
    try:
        # Intentar decodificar si es bytes
        if isinstance(database_url_raw, bytes):
            try:
                database_url_raw = database_url_raw.decode("utf-8")
            except UnicodeDecodeError:
                database_url_raw = database_url_raw.decode("latin-1", errors="ignore")

        # Parsear y reconstruir la URL con encoding correcto para la contraseña
        from urllib.parse import quote_plus, urlparse, urlunparse

        if "@" in database_url_raw and "://" in database_url_raw:
            parsed = urlparse(database_url_raw)
            if parsed.password:
                # Reconstruir la URL con la contraseña codificada
                netloc = f"{parsed.username}:{quote_plus(parsed.password, safe='')}@{parsed.hostname}"
                if parsed.port:
                    netloc += f":{parsed.port}"
                parsed = parsed._replace(netloc=netloc)
                database_url_raw = urlunparse(parsed)
    except Exception:
        # Si falla, usar la URL original
        pass

DATABASE_URL = database_url_raw

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
    ✅ MEJORADO: Rollback preventivo para restaurar transacciones abortadas.
    """
    db = None
    try:
        db = SessionLocal()
        # Test básico de conexión
        try:
            db.execute(text("SELECT 1"))
        except Exception as test_error:
            # Si el test falla, puede ser porque la transacción está abortada
            error_str = str(test_error)
            if "aborted" in error_str.lower() or "InFailedSqlTransaction" in error_str:
                # Intentar rollback para restaurar la transacción
                try:
                    db.rollback()
                    # Reintentar el test después del rollback
                    db.execute(text("SELECT 1"))
                except Exception as rollback_error:
                    logger.warning(f"⚠️ Error al hacer rollback preventivo: {rollback_error}")
                    # Si el rollback también falla, cerrar y crear nueva sesión
                    try:
                        db.close()
                    except Exception:
                        pass
                    db = SessionLocal()
                    db.execute(text("SELECT 1"))
            else:
                # Si no es un error de transacción abortada, re-lanzar
                raise test_error

        yield db
    except Exception as e:
        # Verificar si es un error de autenticación HTTP
        error_str = str(e)
        auth_errors = ["401", "Not authenticated", "Unauthorized"]

        if any(auth_error in error_str for auth_error in auth_errors):
            # Re-lanzar errores de autenticación sin modificar
            raise e

        # NO sobrescribir HTTPException ni RequestValidationError
        if isinstance(e, HTTPException):
            # Re-lanzar HTTPException sin modificar (preservar mensaje)
            raise e

        # NO manejar RequestValidationError de FastAPI (errores de validación de parámetros)
        if isinstance(e, RequestValidationError):
            # Re-lanzar RequestValidationError sin modificar
            raise e

        # Solo manejar errores reales de DB
        error_type = type(e).__name__
        error_message = str(e)
        logger.error(f"Error de base de datos: {error_type}: {error_message}", exc_info=True)

        # Detectar tipos específicos de errores para mensajes más informativos
        error_lower = error_message.lower()
        if "timeout" in error_lower or "timed out" in error_lower:
            detail_message = "Timeout de conexión a la base de datos. El servidor está sobrecargado o la conexión es lenta."
        elif "pool" in error_lower and ("exhausted" in error_lower or "timeout" in error_lower):
            detail_message = (
                "Pool de conexiones agotado. Demasiadas solicitudes simultáneas. Intenta nuevamente en unos momentos."
            )
        elif "connection" in error_lower and ("lost" in error_lower or "closed" in error_lower or "refused" in error_lower):
            detail_message = (
                "Conexión a la base de datos perdida o rechazada. Verifica que el servidor de base de datos esté disponible."
            )
        elif "operationalerror" in error_lower or "connectionerror" in error_lower:
            detail_message = f"Error operacional de base de datos: {error_message[:200]}"
        else:
            # Mensaje genérico pero con más contexto
            detail_message = f"Error de conexión a la base de datos: {error_type}"

        # Crear HTTPException para errores de DB
        raise HTTPException(status_code=500, detail=detail_message)
    finally:
        if db:
            try:
                # ✅ NO hacer commit automático aquí - los endpoints manejan sus propios commits
                # Solo hacer rollback si hay una transacción activa con errores
                # y cerrar la sesión
                try:
                    # Verificar si hay una transacción activa que necesita rollback
                    # Si la sesión está en estado "dirty" o hay errores, hacer rollback
                    if db.in_transaction():
                        # Solo hacer rollback si no se hizo commit explícitamente
                        # Los endpoints ya manejan commits y rollbacks
                        pass  # Dejar que los endpoints manejen sus propios commits/rollbacks
                except Exception:
                    # Si hay error verificando el estado, intentar rollback preventivo
                    try:
                        db.rollback()
                    except Exception:
                        pass
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
