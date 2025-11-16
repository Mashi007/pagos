# backend/app/db/init_db.py
# Database initialization module for the loan management system.
# This module handles database setup, migrations, and admin user creation.

import logging
import traceback
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.user import User

logger = logging.getLogger(__name__)


def run_migrations() -> None:
    """Ejecutar migraciones de Alembic automáticamente."""
    try:
        from pathlib import Path

        from alembic import command
        from alembic.config import Config

        # Obtener ruta del archivo alembic.ini
        alembic_ini_path = Path(__file__).parent.parent.parent / "alembic.ini"

        if not alembic_ini_path.exists():
            logger.warning("⚠️ alembic.ini no encontrado, omitiendo migraciones automáticas")
            return

        # Configurar Alembic
        alembic_cfg = Config(str(alembic_ini_path))
        alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

        logger.info("=" * 60)
        logger.info("🔄 EJECUTANDO MIGRACIONES DE ALEMBIC...")
        logger.info("=" * 60)
        # Verificar si hay múltiples heads
        from alembic.script import ScriptDirectory

        script = ScriptDirectory.from_config(alembic_cfg)
        heads = script.get_revisions("heads")
        logger.info(f"📊 Total de heads detectados: {len(heads)}")

        if len(heads) > 1:
            # Si hay múltiples heads, primero actualizar a todos los heads individuales
            # y luego al merge point si existe
            logger.info(f"⚠️ Múltiples heads detectados ({len(heads)}), actualizando todos primero...")
            for head in heads:
                try:
                    logger.info(f"📌 Actualizando a head: {head.revision}")
                    command.upgrade(alembic_cfg, head.revision)
                except Exception as head_error:
                    logger.warning(f"⚠️ Error actualizando head {head.revision}: {head_error}")
                    # Continuar con el siguiente head

            # Después de actualizar todos los heads, intentar actualizar al merge point
            try:
                merge_point = script.get_revision("9537ffbe05a6")
                if merge_point:
                    logger.info("📌 Actualizando a merge point 9537ffbe05a6 (incluye migraciones AI training)...")
                    command.upgrade(alembic_cfg, "9537ffbe05a6")
            except Exception as merge_error:
                logger.warning(f"⚠️ No se pudo actualizar al merge point (puede que ya esté aplicado): {merge_error}")
        else:
            # Un solo head, actualizar normalmente
            command.upgrade(alembic_cfg, "head")
        logger.info("=" * 60)
        logger.info("✅ MIGRACIONES DE ALEMBIC EJECUTADAS EXITOSAMENTE")
        logger.info("=" * 60)

    except ImportError:
        logger.warning("⚠️ Alembic no está disponible, omitiendo migraciones automáticas")
    except Exception as e:
        logger.error(f"❌ Error ejecutando migraciones de Alembic: {e}")
        logger.error(traceback.format_exc())
        # No lanzar excepción para no bloquear el startup si las migraciones fallan
        # Las migraciones pueden ejecutarse manualmente si es necesario


def init_db_startup() -> None:
    """Initialize database on startup."""
    try:
        logger.info("Starting database initialization...")

        # Create database if it doesn't exist
        engine = create_engine(settings.DATABASE_URL)

        with engine.connect() as conn:
            # Test connection
            conn.execute(text("SELECT 1"))
            logger.info("Database connection successful")

        # Ejecutar migraciones de Alembic automáticamente
        run_migrations()

        # Create admin user if it doesn't exist
        create_admin_user()

        logger.info("Database initialization completed successfully")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        logger.error(traceback.format_exc())
        raise


def init_db_shutdown() -> None:
    """Cleanup on shutdown."""
    try:
        logger.info("Database shutdown cleanup completed")
    except Exception as e:
        logger.error(f"Database shutdown cleanup failed: {e}")


def create_admin_user() -> None:
    """Create admin user if it doesn't exist."""
    try:
        db = SessionLocal()

        # Usar configuración desde settings
        admin_email = settings.ADMIN_EMAIL
        admin_password = settings.ADMIN_PASSWORD

        if not admin_email or not admin_password:
            logger.warning("⚠️ ADMIN_EMAIL o ADMIN_PASSWORD no configurados. " "Omitiendo creación de usuario admin.")
            return

        # Check if admin user exists
        admin_user = db.query(User).filter(User.email == admin_email).first()

        if not admin_user:
            # Create admin user usando configuración desde settings
            admin_user = User(
                email=admin_email,
                hashed_password=get_password_hash(admin_password),
                rol="ADMIN",
                is_admin=True,
                is_active=True,
                nombre="IT Master",
                apellido="RapiCredit",
            )

            db.add(admin_user)
            db.commit()
            logger.info("Admin user created successfully")
        else:
            logger.info("Admin user already exists")

    except Exception as e:
        logger.error(f"Error creating admin user: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
