"""
Conexión a la base de datos PostgreSQL.
Proporciona engine, sesión y dependencia get_db para inyectar en endpoints.
"""
import logging
import os
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, declarative_base

from app.core.config import settings

logger = logging.getLogger(__name__)

# Zona usada en SET timezone por conexión y en SQL explícito (KPIs “mes actual”).
BUSINESS_TIMEZONE = "America/Caracas"


def _resolve_statement_timeout_ms() -> int:
    """
    Lee `PG_STATEMENT_TIMEOUT_MS` del entorno y devuelve el valor a aplicar como
    `statement_timeout` en cada conexión nueva.

    Default: 300000 ms (5 min). Es defensa contra queries degeneradas (join cartesiano,
    estimación rota del planner, función recursiva sin tope) que con `--workers 1`
    bloquearían al único proceso atendiendo peticiones.

    Cualquier flujo legítimo > 5 min:
      - GET listado-y-kpis: 1-10 s típico, < 30 s en peor caso → cubierto.
      - PATCH estado/editar: < 30 s → cubierto.
      - Exports Excel grandes: pueden acercarse a 1-2 min → cubierto.
      - Notificaciones masivas: el trabajo lento NO es SQL sino SMTP (cada destino tiene
        su propia conexión SMTP); las queries puntuales son cortas.
      - Drive import bulk: igual, cuello SMTP/Drive API, no Postgres.

    Para subir el techo, configurar en Render Dashboard:
      PG_STATEMENT_TIMEOUT_MS=600000   # 10 min
    Para desactivar (no recomendado):
      PG_STATEMENT_TIMEOUT_MS=0
    """
    raw = os.environ.get("PG_STATEMENT_TIMEOUT_MS", "300000").strip()
    try:
        v = int(raw)
        # Clamp defensivo: si alguien pone -1 o un valor absurdo, volvemos al default.
        if v < 0:
            return 300_000
        # 0 = desactivado (lo permitimos pero advertimos en startup).
        return v
    except ValueError:
        return 300_000


_PG_STATEMENT_TIMEOUT_MS = _resolve_statement_timeout_ms()

# Asegurar que la URL use el driver postgresql (Render suele dar postgres://)
_db_url = settings.DATABASE_URL
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql://", 1)

_is_postgres = _db_url.startswith("postgresql")

if _is_postgres:
    _engine_kwargs = dict(
        pool_pre_ping=True,  # Verifica que la conexión esté viva antes de usarla (reconexión automática)
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_recycle=300,  # Recicla cada 5 min (Render cierra SSL antes; evita SSL connection closed unexpectedly)
        pool_timeout=settings.DATABASE_POOL_TIMEOUT,
        connect_args={
            "connect_timeout": 15,  # Timeout de conexión inicial (psycopg2)
            "application_name": "rapicredit_backend",
            "keepalives": 1,  # Habilitar TCP keepalives (psycopg2 nativo)
            "keepalives_idle": 30,  # Inicia keepalive tras 30s de inactividad
            "keepalives_interval": 10,  # Envía keepalive cada 10s
            "keepalives_count": 5,  # Máximo 5 keepalives sin respuesta antes de cerrar
        },
        echo=False,
        pool_use_lifo=True,  # QueuePool: bajo ráfagas, LIFO reutiliza conexiones recientes
    )
    engine = create_engine(_db_url, **_engine_kwargs)
else:
    # SQLite (p. ej. pytest): no acepta pool_size/max_overflow ni connect_args de psycopg2.
    _non_pg_kwargs: dict = {"echo": False}
    if _db_url.startswith("sqlite"):
        _non_pg_kwargs["connect_args"] = {"check_same_thread": False}
    engine = create_engine(_db_url, **_non_pg_kwargs)

@event.listens_for(engine, "connect")
def _set_timezone_vzla(dbapi_connection, connection_record):
    """Set session timezone to Venezuela (America/Caracas) for every new connection."""
    if not _is_postgres:
        return
    cursor = dbapi_connection.cursor()
    cursor.execute(f"SET timezone = '{BUSINESS_TIMEZONE}'")
    cursor.close()


@event.listens_for(engine, "connect")
def _set_statement_timeout(dbapi_connection, connection_record):
    """
    Aplica `statement_timeout` (ms) a cada nueva conexión Postgres.

    Una query atascada en el único worker (workers=1 en Render) bloquearía a TODA la app
    hasta que gunicorn `--timeout` la corte (con la mala señal de matar al worker entero).
    Postgres puede cancelar la query individualmente sin tocar el proceso Python si
    `statement_timeout` está configurado. Resulta en un error SQL recuperable que el
    endpoint puede manejar (HTTP 500 limpio + logs), no en restart del dyno.

    Configurable vía env `PG_STATEMENT_TIMEOUT_MS`. Ver `_resolve_statement_timeout_ms()`.

    `0` desactiva el límite; en ese caso, no ejecutamos SET (evita ruido).
    """
    if not _is_postgres:
        return
    if _PG_STATEMENT_TIMEOUT_MS <= 0:
        return
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute(f"SET statement_timeout = {int(_PG_STATEMENT_TIMEOUT_MS)}")
        cursor.close()
    except Exception as e:
        # Log defensivo: si el server PG no lo soporta (raro, está en core desde 8.x),
        # no abortar la conexión. Los endpoints seguirán funcionando, solo perdemos la
        # red de seguridad de timeout por query.
        try:
            logger.warning(
                "[DB] No se pudo aplicar statement_timeout=%sms a la conexión nueva: %s",
                _PG_STATEMENT_TIMEOUT_MS,
                e,
            )
        except Exception:
            pass


# Aviso único en logs al cargar el módulo: ayuda a confirmar el valor activo durante el
# análisis de un incidente futuro. `logger.info` queda visible en Render por defecto.
if _is_postgres:
    if _PG_STATEMENT_TIMEOUT_MS <= 0:
        logger.warning(
            "[DB] statement_timeout DESACTIVADO (PG_STATEMENT_TIMEOUT_MS=%s). "
            "Una query atascada puede bloquear al worker; reactivar configurando "
            "PG_STATEMENT_TIMEOUT_MS>0 en el entorno.",
            _PG_STATEMENT_TIMEOUT_MS,
        )
    else:
        logger.info(
            "[DB] statement_timeout=%sms aplicado por conexión (env PG_STATEMENT_TIMEOUT_MS).",
            _PG_STATEMENT_TIMEOUT_MS,
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
