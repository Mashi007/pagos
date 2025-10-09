from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Crear engine con configuración optimizada
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,  # Verifica conexiones antes de usarlas
    echo=settings.DEBUG,  # SQL logging solo en desarrollo
)

# SessionLocal para crear sesiones de base de datos
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base para modelos
Base = declarative_base()


def get_db():
    """
    Dependency para FastAPI que provee una sesión de base de datos.
    Se cierra automáticamente después de cada request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
