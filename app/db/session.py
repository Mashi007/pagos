# app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Motor de base de datos
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.ENVIRONMENT == "development",
)

# Sesión
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Generador de sesiones de BD"""
    db = SessionLocal()
    try:
        logger.info("✅ Conexión a BD abierta")
        yield db
    except Exception as e:
        logger.error(f"❌ Error en sesión BD: {str(e)}")
        raise
    finally:
        db.close()
        logger.info("🔒 Conexión a BD cerrada")
