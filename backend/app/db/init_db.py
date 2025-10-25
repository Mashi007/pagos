# backend/app/db/init_db.py
"""
Database initialization module for the loan management system.
This module handles database setup, migrations, and admin user creation.
"""
import logging
import os
import subprocess
import traceback
from datetime import datetime

from sqlalchemy import inspect, text

from app.core.config import settings
from app.db.session import Base, SessionLocal, engine
from app.models.user import User

# Constantes de configuración
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_SEPARATOR_LENGTH = 50
MAIN_TABLES = ["usuarios", "clientes", "prestamos", "pagos"]

logger = logging.getLogger(__name__)


def check_database_connection() -> bool:
    """Verifica si la conexión a la base de datos está funcionando"""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Error conectando a base de datos: {e}")
        return False


def table_exists(table_name: str) -> bool:
    """Verifica si una tabla existe en la base de datos"""
    try:
        inspector = inspect(engine)
        return table_name in inspector.get_table_names()
    except Exception as e:
        logger.error(f"Error verificando tabla {table_name}: {e}")
        return False


def create_tables():
    """Crea todas las tablas definidas en los modelos"""
    try:
        # Importar models para registrar en metadata
        import app.models  # noqa

        # Crear tablas
        Base.metadata.create_all(bind=engine)
        logger.info("Tablas creadas exitosamente")
        return True
    except Exception as e:
        logger.error(f"Error creando tablas: {e}")
        return False


def run_migrations():
    """Ejecuta las migraciones de Alembic"""
    try:
        # Cambiar al directorio del backend
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        os.chdir(backend_dir)

        logger.info("🔄 Ejecutando migraciones de Alembic...")

        # Ejecutar alembic upgrade head
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )

        if result.returncode == 0:
            logger.info("Migraciones aplicadas exitosamente")
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
        existing_admin = db.query(User).filter(User.email == "itmaster@rapicreditca.com").first()

        if existing_admin:
            logger.info(f"Usuario itmaster@rapicreditca.com ya existe: {existing_admin.email}")
            db.close()
            return True

        # Eliminar admin@financiamiento.com si existe
        wrong_admin = db.query(User).filter(User.email == "admin@financiamiento.com").first()
        if wrong_admin:
            logger.info(f"Eliminando usuario incorrecto: {wrong_admin.email}")
            db.delete(wrong_admin)
            db.commit()

        logger.info("Creando usuario administrador...")

        # Crear admin con las credenciales desde settings
        admin = User(
            email=settings.ADMIN_EMAIL,
            nombre="IT Master",
            apellido="Sistema",
            hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
            is_admin=True,  # Cambio clave: rol → is_admin
            is_active=True,
            created_at=datetime.utcnow(),
        )

        db.add(admin)
        db.commit()
        db.refresh(admin)

        logger.info("Usuario ADMIN creado exitosamente")
        logger.info(f"Email: {admin.email}")
        logger.info("Password: (ver settings.ADMIN_PASSWORD)")

        db.close()
        return True

    except LookupError as e:
        # Error de enum - esto es esperado si la DB tiene roles antiguos
        logger.warning(f"Error de enum detectado (esperado): {e}")
        logger.warning("Esto se resolverá ejecutando /api/v1/emergency/migrate-roles")
        return False
    except Exception as e:
        logger.error(f"Error creando usuario admin: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False


def init_db() -> bool:
    """Inicializa la base de datos creando las tablas si no existen"""
    try:
        logger.info("Inicializando base de datos...")

        if not check_database_connection():
            logger.error("No se pudo conectar a la base de datos")
            return False

        # NO ejecutar migraciones automáticamente para evitar conflictos con enum
        # Las migraciones deben ejecutarse manualmente vía endpoint de emergencia
        logger.info("Saltando migraciones automáticas (usar endpoint de emergencia si es necesario)")

        tables_exist = all(table_exists(table) for table in MAIN_TABLES)

        if not tables_exist:
            logger.info("Tablas no encontradas, creando...")
            if create_tables():
                logger.info("Base de datos inicializada correctamente")
                # Crear usuario admin después de crear tablas
                create_admin_user()
                return True
            else:
                logger.error("Error al crear tablas")
                return False
        else:
            logger.info("Base de datos ya inicializada, tablas existentes")
            # Intentar crear usuario admin si no existe (puede fallar con enum error)
            create_admin_user()
            return True

    except Exception as e:
        logger.error(f"Error inicializando base de datos: {e}")
        return False


init_database = init_db


def init_db_startup():
    """Función que se llama al inicio de la aplicación"""
    try:
        logger.info("\n" + "=" * DEFAULT_SEPARATOR_LENGTH)
        logger.info(f"Sistema de Préstamos y Cobranza v{settings.APP_VERSION}")
        logger.info("=" * DEFAULT_SEPARATOR_LENGTH)
        logger.info(f"Base de datos: {settings.get_database_url(hide_password=True)}")

        # Intentar inicializar la base de datos pero no fallar si no se puede conectar
        db_initialized = False
        try:
            if init_db():
                if check_database_connection():
                    logger.info("Conexión a base de datos verificada")
                    db_initialized = True
                else:
                    logger.warning("Advertencia: Problema de conexión a base de datos")
            else:
                logger.warning("Advertencia: Error inicializando tablas")
        except Exception as db_error:
            logger.error(f"Error de base de datos (la aplicación continuará): {db_error}")

        if not db_initialized:
            logger.warning("La aplicación iniciará en modo de funcionalidad limitada")
            logger.warning("Algunas funciones pueden no estar disponibles")

        logger.info(f"Entorno: {settings.ENVIRONMENT}")
        logger.info("Documentación: /docs")
        logger.info(f"Debug mode: {'ON' if settings.DEBUG else 'OFF'}")
        logger.info("=" * DEFAULT_SEPARATOR_LENGTH)
        logger.info("")

    except Exception as e:
        logger.error(f"Error en startup de DB: {e}")
        logger.warning("Continuando sin conexión a base de datos")


def init_db_shutdown():
    """Función que se llama al cerrar la aplicación"""
    try:
        from app.db.session import close_db_connections

        close_db_connections()
        logger.info("")
        logger.info("Sistema de Préstamos y Cobranza detenido")
    except Exception as e:
        logger.error(f"Error en shutdown de DB: {e}")
