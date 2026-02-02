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
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
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
