# backend/app/db/init_db.py
"""Database initialization module for the loan management system.

This module handles database setup, migrations, and admin user creation.
"""

import logging
import subprocess
import traceback

from sqlalchemy import inspect, text

from app.core.config import settings
from app.db.session import Base, SessionLocal, engine
from app.models.user import User

# Constantes de configuración
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_SEPARATOR_LENGTH = 50

logger = logging.getLogger(__name__)


def check_database_connection() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as e:
        return False


def table_exists(table_name: str) -> bool:
    try:
        inspector = inspect(engine)
        return table_name in inspector.get_table_names()
    except Exception as e:
        logger.error(f"Error verificando tabla {table_name}: {e}")
        return False


def create_tables():
    try:
        # Importar models para registrar en metadata

        # Crear tablas
        Base.metadata.create_all(bind=engine)
        return True
    except Exception as e:
        logger.error(f"Error creando tablas: {e}")
        return False


def run_migrations():
    """Ejecuta las migraciones de Alembic"""
    try:
        # Cambiar al directorio del backend

        logger.info("🔄 Ejecutando migraciones de Alembic...")

        # Ejecutar alembic upgrade head
        result = subprocess.run

        if result.returncode == 0:
            return True
        else:
            logger.error(f"Error ejecutando migraciones: {result.stderr}")
            return False

    except Exception as e:
        logger.error(f"Error ejecutando migraciones: {e}")
        return False


def create_admin_user():
    """Crea el usuario administrador si no existe"""
    try:
        logger.info("🔄 Verificando usuario administrador...")
        from app.core.security import get_password_hash

        db = SessionLocal()

        # Verificar si ya existe el admin correcto
        existing_admin = 
            db.query(User)
            .filter(User.email == "itmaster@rapicreditca.com")
            .first()

        if existing_admin:
            logger.info
            return True

        # Eliminar admin@financiamiento.com si existe
        wrong_admin = 
            db.query(User)
            .filter(User.email == "admin@financiamiento.com")
            .first()

        if wrong_admin:
            logger.info(f"Eliminando usuario incorrecto: {wrong_admin.email}")
            db.delete(wrong_admin)
            db.commit()

        logger.info("Creando usuario administrador...")

        # Crear admin con las credenciales desde settings
        admin = User
            hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
            is_admin=True,  # Cambio clave: rol → is_admin
            is_active=True,

        db.add(admin)
        db.commit()
        db.refresh(admin)

        logger.info(f"Email: {admin.email}")
        logger.info("Password: (ver settings.ADMIN_PASSWORD)")

        return True

    except LookupError as e:
        logger.warning(f"Error de enum detectado (esperado): {e}")
        logger.warning
        return False

    except Exception as e:
        logger.error(f"Error creando usuario admin: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False


def init_db() -> bool:
    try:

        if not check_database_connection():
            return False

        # NO ejecutar migraciones automáticamente
        # Las migraciones deben ejecutarse manualmente vía endpoint de emergencia
        logger.info
            "(usar endpoint de emergencia si es necesario)"

        tables_exist = all(table_exists(table) for table in MAIN_TABLES)

        if not tables_exist:
            logger.info("Tablas no encontradas, creando...")
            if create_tables():
                # Crear usuario admin después de crear tablas
                create_admin_user()
                return True
            else:
                logger.error("Error al crear tablas")
                return False
        else:
            # Intentar crear usuario admin si no existe (puede fallar con enum error)
            create_admin_user()
            return True

    except Exception as e:
        return False


# Alias para compatibilidad
init_database = init_db


def init_db_startup():
    """Función que se llama al inicio de la aplicación"""
    try:
        logger.info("\n" + "=" * DEFAULT_SEPARATOR_LENGTH)
        logger.info("=" * DEFAULT_SEPARATOR_LENGTH)
        logger.info

        # no fallar si no se puede conectar
        db_initialized = False

        try:
            if init_db():
                if check_database_connection():
                    db_initialized = True
                else:
                    logger.warning
            else:
                logger.warning("Advertencia: Error inicializando tablas")

        except Exception as db_error:
            logger.error

        if not db_initialized:
            logger.warning
            logger.warning("Algunas funciones pueden no estar disponibles")

        logger.info(f"Entorno: {settings.ENVIRONMENT}")
        logger.info("Documentación: /docs")
        logger.info(f"Debug mode: {'ON' if settings.DEBUG else 'OFF'}")
        logger.info("=" * DEFAULT_SEPARATOR_LENGTH)
        logger.info("")

    except Exception as e:
        logger.error(f"Error en startup de DB: {e}")


def init_db_shutdown():
    """Función que se llama al cerrar la aplicación"""
    try:
        logger.info("")
    except Exception as e:
        logger.error(f"Error en shutdown de DB: {e}")
