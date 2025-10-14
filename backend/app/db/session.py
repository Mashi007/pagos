# backend/app/db/session.py
"""
Configuración de SQLAlchemy: Engine, SessionLocal y Base.
"""
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ✅ CORRECTO: Importar desde app.core.config
from app.core.config import settings

# Crear engine de SQLAlchemy
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=1,  # Reducido para Render
    max_overflow=0,  # Sin overflow para evitar problemas
    pool_timeout=10,  # Timeout más corto
    pool_recycle=300,  # Reciclar cada 5 minutos
    echo=settings.DB_ECHO,
    connect_args={
        "connect_timeout": 10,
        "application_name": "rapicredit_backend"
    }
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
    db = None
    try:
        # Intentar crear sesión con timeout
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("🔄 Intentando crear sesión de base de datos...")
        db = SessionLocal()
        
        # Test de conexión
        db.execute(text("SELECT 1"))
        logger.info("✅ Sesión de base de datos creada exitosamente")
        
        yield db
        
    except Exception as e:
        # Log del error detallado
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"❌ Error de conexión a base de datos: {e}")
        logger.error(f"❌ Tipo de error: {type(e).__name__}")
        
        # Importar HTTPException dentro de la función para evitar imports circulares
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503, 
            detail="Servicio de base de datos temporalmente no disponible"
        )
    finally:
        if db:
            try:
                db.close()
                logger.info("✅ Sesión de base de datos cerrada")
            except Exception as e:
                logger.warning(f"⚠️ Error cerrando sesión: {e}")


def close_db_connections():
    """Cierra todas las conexiones de la pool al shutdown"""
    engine.dispose()
