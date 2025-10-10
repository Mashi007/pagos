# app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)

# Obtener configuración
settings = get_settings()

# Fix para Railway: postgres:// → postgresql://
DATABASE_URL = settings.DATABASE_URL
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    logger.info("🔧 Corregido DATABASE_URL: postgres:// → postgresql://")

# Crear engine con configuración para producción
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,      # Verifica conexiones antes de usarlas
    pool_recycle=3600,       # Recicla conexiones cada hora
    pool_size=5,             # Tamaño del pool
    max_overflow=10,         # Conexiones extra permitidas
    echo=settings.DEBUG,     # SQL logging solo en debug
)

# Crear SessionLocal
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def get_db():
    """
    Dependency para obtener sesión de base de datos
    
    Yields:
        Session: Sesión de SQLAlchemy
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
