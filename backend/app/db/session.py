# backend/app/db/session.py
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool, QueuePool
from app.core.config import get_settings  # ✅ CORREGIDO
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

# ============================================
# CONFIGURACIÓN DEL ENGINE
# ============================================

# Argumentos base del engine
engine_args = {
    "echo": settings.DB_ECHO,
    "future": True,  # SQLAlchemy 2.0 style
}

# En producción, usar pool de conexiones
if settings.is_production:
    engine_args.update({
        "poolclass": QueuePool,
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_timeout": settings.DB_POOL_TIMEOUT,
        "pool_recycle": settings.DB_POOL_RECYCLE,
        "pool_pre_ping": True,  # Verifica conexiones antes de usarlas
    })
    logger.info(f"🔵 DB Pool configurado: size={settings.DB_POOL_SIZE}, max_overflow={settings.DB_MAX_OVERFLOW}")
else:
    # En desarrollo, pool simple o sin pool
    engine_args["poolclass"] = NullPool
    logger.info("🟡 DB Pool deshabilitado (desarrollo)")

# Crear engine
try:
    engine = create_engine(
        settings.DATABASE_URL,
        **engine_args
    )
    logger.info(f"✅ Engine creado: {settings.get_database_url(hide_password=True)}")
except Exception as e:
    logger.error(f"❌ Error creando engine: {e}")
    raise

# ============================================
# SESSION FACTORY
# ============================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Mejor performance
)

# ============================================
# BASE PARA MODELOS
# ============================================

Base = declarative_base()

# ============================================
# EVENTOS DE CONEXIÓN (Logging y Debugging)
# ============================================

@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Evento cuando se establece una nueva conexión"""
    if settings.DEBUG:
        logger.debug(f"🔗 Nueva conexión DB establecida")


@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Evento cuando se obtiene una conexión del pool"""
    if settings.DEBUG:
        logger.debug(f"📤 Conexión obtenida del pool")


@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_conn, connection_record):
    """Evento cuando se devuelve una conexión al pool"""
    if settings.DEBUG:
        logger.debug(f"📥 Conexión devuelta al pool")


# ============================================
# DEPENDENCY INJECTION
# ============================================

def get_db():
    """
    Dependency para FastAPI
    Crea y cierra sesiones automáticamente
    
    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================
# UTILIDADES
# ============================================

def get_db_info() -> dict:
    """
    Retorna información sobre el pool de conexiones
    Útil para debugging y monitoreo
    """
    pool = engine.pool
    
    info = {
        "pool_size": getattr(pool, "size", lambda: 0)(),
        "checked_out": getattr(pool, "checkedout", lambda: 0)(),
        "overflow": getattr(pool, "overflow", lambda: 0)(),
        "checkedin": getattr(pool, "checkedin", lambda: 0)(),
        "is_production": settings.is_production,
        "pool_class": pool.__class__.__name__,
    }
    
    return info


async def check_db_connection() -> bool:
    """
    Verifica si la conexión a la base de datos está funcionando
    Útil para health checks
    """
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return True
    except Exception as e:
        logger.error(f"❌ Error verificando conexión DB: {e}")
        return False


def close_db_connections():
    """
    Cierra todas las conexiones del pool
    Útil para shutdown graceful
    """
    try:
        engine.dispose()
        logger.info("✅ Conexiones DB cerradas correctamente")
    except Exception as e:
        logger.error(f"❌ Error cerrando conexiones: {e}")
