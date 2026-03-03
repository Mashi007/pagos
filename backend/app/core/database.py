"""
Conexión a la base de datos PostgreSQL.
Proporciona engine, sesión y dependencia get_db para inyectar en endpoints.
"""
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base

from app.core.config import settings

# Asegurar que la URL use el driver postgresql (Render suele dar postgres://)
_db_url = settings.DATABASE_URL
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    _db_url,
    # Configuración de pool optimizada para Render (PostgreSQL con SSL inestable)
    pool_pre_ping=True,  # Verifica que la conexión esté viva antes de usarla
    pool_size=10,  # Más conexiones en pool (mejor concurrencia)
    max_overflow=20,  # Permite más conexiones temporales si es necesario
    pool_recycle=3600,  # Recicla conexiones cada hora (evita stale connections)
    pool_timeout=30,  # Timeout esperando conexión disponible (en segundos)
    connect_args={
        "connect_timeout": 30,  # Timeout de conexión inicial (aumentado)
        "application_name": "rapicredit_backend",
        "sslmode": "require",  # Fuerza SSL para seguridad
        "tcp_keepalives": True,  # Mantiene conexión viva
        "tcp_keepalives_idle": 30,
        "tcp_keepalives_interval": 10,
    },
    echo=False,  # Cambiar a True para logging de SQL si es necesario en DEBUG
)

# expire_on_commit=False evita el error F405: al cerrar la sesión los objetos no se "expiran",
# así la serialización de la respuesta (Pydantic/model_validate) no intenta lazy load fuera de la sesión.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependencia FastAPI: sesión de BD por request. Cierra al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
