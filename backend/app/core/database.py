"""
Conexión a la base de datos PostgreSQL.
Proporciona engine, sesión y dependencia get_db para inyectar en endpoints.
"""
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, declarative_base

from app.core.config import settings

# Asegurar que la URL use el driver postgresql (Render suele dar postgres://)
_db_url = settings.DATABASE_URL
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    _db_url,
    pool_pre_ping=True,   # Verifica que la conexión esté viva antes de usarla (reconexión automática)
    pool_size=10,          # Conexiones mantenidas en pool
    max_overflow=20,       # Conexiones adicionales permitidas bajo carga
    pool_recycle=1800,     # Recicla conexiones cada 30 min (evita SSL stale)
    pool_timeout=30,       # Tiempo max esperando conexión disponible
    connect_args={
        "connect_timeout": 15,        # Timeout de conexión inicial (psycopg2)
        "application_name": "rapicredit_backend",
        "keepalives": 1,              # Habilitar TCP keepalives (psycopg2 nativo)
        "keepalives_idle": 60,        # Inicia keepalive tras 60s de inactividad
        "keepalives_interval": 10,    # Envía keepalive cada 10s
        "keepalives_count": 5,        # Máximo 5 keepalives sin respuesta antes de cerrar
    },
    echo=False,
)

@event.listens_for(engine, "connect")
def _set_timezone_vzla(dbapi_connection, connection_record):
    """Set session timezone to Venezuela (America/Caracas) for every new connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("SET timezone = 'America/Caracas'")
    cursor.close()


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
