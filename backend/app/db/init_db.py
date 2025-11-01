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

        # Check if admin user exists
        admin_user = db.query(User).filter(User.email == "itmaster@rapicreditca.com").first()

        if not admin_user:
            # Create admin user
            admin_user = User(
                email="itmaster@rapicreditca.com",
                hashed_password=get_password_hash("R@pi_2025**"),
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
