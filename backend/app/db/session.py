# backend/app/db/session.py
"""
Configuración de SQLAlchemy: Engine, SessionLocal y Base.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ✅ CORREGIDO: Importar desde app.core.config
from app.core.config import settings


# Crear engine de SQLAlchemy
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    echo=settings.DB_ECHO  # Mostrar queries SQL si está habilitado
)

# SessionLocal para crear sesiones de BD
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base para los modelos
Base = declarative_base()


# Dependency para FastAPI
def get_db():
    """
    Dependency que proporciona una sesión de base de datos.
    Se cierra automáticamente después de cada request.
    
    Uso en endpoints:
        @router.get("/clientes")
        def get_clientes(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
