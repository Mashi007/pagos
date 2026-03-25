"""
Conexión a la base de datos PostgreSQL.
Proporciona engine, sesión y dependencia get_db para inyectar en endpoints.
"""
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, declarative_base

from app.core.config import settings

# Zona usada en SET timezone por conexión y en SQL explícito (KPIs “mes actual”).
BUSINESS_TIMEZONE = "America/Caracas"

# Asegurar que la URL use el driver postgresql (Render suele dar postgres://)
_db_url = settings.DATABASE_URL
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    _db_url,
    pool_pre_ping=True,   # Verifica que la conexión esté viva antes de usarla (reconexión automática)
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_recycle=300,     # Recicla cada 5 min (Render cierra SSL antes; evita SSL connection closed unexpectedly)
    pool_timeout=settings.DATABASE_POOL_TIMEOUT,
    connect_args={
        "connect_timeout": 15,        # Timeout de conexión inicial (psycopg2)
        "application_name": "rapicredit_backend",
        "keepalives": 1,              # Habilitar TCP keepalives (psycopg2 nativo)
        "keepalives_idle": 30,        # Inicia keepalive tras 30s de inactividad
        "keepalives_interval": 10,    # Envía keepalive cada 10s
        "keepalives_count": 5,        # Máximo 5 keepalives sin respuesta antes de cerrar
    },
    echo=False,
)

@event.listens_for(engine, "connect")
def _set_timezone_vzla(dbapi_connection, connection_record):
    """Set session timezone to Venezuela (America/Caracas) for every new connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute(f"SET timezone = '{BUSINESS_TIMEZONE}'")
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
