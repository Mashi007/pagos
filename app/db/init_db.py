# app/db/init_db.py
from sqlalchemy import inspect
from app.db.session import engine
from app.db.base import Base
from app.models import Cliente, Pago
import logging

logger = logging.getLogger(__name__)

def init_database():
    """Crea todas las tablas en la base de datos"""
    try:
        logger.info("=" * 60)
        logger.info("🔧 Iniciando creación de tablas...")
        
        # Verificar tablas existentes
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        logger.info(f"📊 Tablas existentes: {existing_tables}")
        
        # Crear todas las tablas
        Base.metadata.create_all(bind=engine)
        
        # Verificar tablas creadas
        new_tables = inspector.get_table_names()
        logger.info(f"✅ Tablas después de crear: {new_tables}")
        logger.info("✅ Base de datos inicializada correctamente")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error inicializando BD: {str(e)}")
        raise
