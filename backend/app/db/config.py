import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import logging

logger = logging.getLogger(__name__)

# Configuración de la base de datos
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://user:password@localhost/dbname"
)

# Para Render, a veces necesitamos usar la URL externa
RENDER_DATABASE_URL = os.getenv("RENDER_DATABASE_URL")
if RENDER_DATABASE_URL:
    DATABASE_URL = RENDER_DATABASE_URL

# Configuración del motor de base de datos con mejores parámetros para Render
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_recycle=300,
    pool_pre_ping=True,  # Verifica la conexión antes de usar
    connect_args={
        "connect_timeout": 10,
        "application_name": "sistema-prestamos-cobranza"
    }
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency para obtener sesión de base de datos"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Error en sesión de base de datos: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def test_connection():
    """Prueba la conexión a la base de datos"""
    try:
        with engine.connect() as connection:
            result = connection.execute("SELECT 1")
            logger.info("✅ Conexión a base de datos exitosa")
            return True
    except Exception as e:
        logger.error(f"❌ Error probando conexión: {e}")
        return False