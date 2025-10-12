# backend/app/db/session.py
"""
Configuración de SQLAlchemy: Engine, SessionLocal y Base.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ✅ CORRECTO: Importar desde app.core.config
from app.core.config import settings

# Crear engine de SQLAlchemy
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    echo=settings.DB_ECHO
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
    
    Si hay problemas de conexión, levanta HTTPException apropiada.
    """
    try:
        db = SessionLocal()
        yield db
    except Exception as e:
        # Log del error pero no exponer detalles técnicos al usuario
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error de conexión a base de datos: {e}")
        
        # Importar HTTPException dentro de la función para evitar imports circulares
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503, 
            detail="Servicio de base de datos temporalmente no disponible"
        )
    finally:
        try:
            db.close()
        except:
            pass  # Si db no se creó, no hay nada que cerrar


def close_db_connections():
    """Cierra todas las conexiones de la pool al shutdown"""
    engine.dispose()
