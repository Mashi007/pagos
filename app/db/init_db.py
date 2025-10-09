# app/db/init_db.py
from sqlalchemy import text
from app.db.session import engine, Base
from app.models import cliente, prestamo, pago
import logging

logger = logging.getLogger(__name__)

def init_database():
    """Inicializa las tablas de la base de datos"""
    try:
        logger.info("📊 Iniciando creación de tablas...")
        
        # Crear todas las tablas
        Base.metadata.create_all(bind=engine)
        
        logger.info("✅ Tablas creadas exitosamente")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error inicializando BD: {e}")
        return False

def check_database_connection():
    """Verifica la conexión a la base de datos"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        logger.info("✅ Conexión a BD exitosa")
        return True
    except Exception as e:
        logger.error(f"❌ Error conectando a BD: {e}")
        return False
