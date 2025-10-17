# backend/app/db/session.py
"""
Configuración de SQLAlchemy: Engine, SessionLocal y Base.
"""
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging

# ✅ CORRECTO: Importar desde app.core.config
from app.core.config import settings

# Configurar logger
logger = logging.getLogger(__name__)

# Crear engine de SQLAlchemy con configuración optimizada para producción
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # ✅ Verifica conexión antes de usar
    pool_size=5,  # ✅ 5 conexiones permanentes (aumentado)
    max_overflow=10,  # ✅ 10 conexiones adicionales si es necesario
    pool_timeout=30,  # ✅ 30 segundos timeout (aumentado)
    pool_recycle=3600,  # ✅ Reciclar cada hora (más estable)
    echo=settings.DB_ECHO,
    connect_args={
        "connect_timeout": 30,  # ✅ 30 segundos para conectar
        "application_name": "rapicredit_backend",
        "options": "-c statement_timeout=30000"  # ✅ 30 segundos para queries
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
        # Crear sesión de base de datos
        db = SessionLocal()
        
        # Test básico de conexión (sin logging excesivo)
        db.execute(text("SELECT 1"))
        
        yield db
        
    except Exception as e:
        # Solo manejar errores reales de DB, no de autenticación
        
        # Verificar si es un error de autenticación HTTP
        error_str = str(e)
        if "401" in error_str or "Not authenticated" in error_str or "Email o contraseña incorrectos" in error_str:
            # Re-lanzar errores de autenticación sin modificar
            raise e
        
        # Solo manejar errores reales de DB
        logger.error(f"❌ Error real de base de datos: {e}")
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
            except Exception:
                pass  # Ignorar errores al cerrar


def close_db_connections():
    """Cierra todas las conexiones de la pool al shutdown"""
    engine.dispose()
