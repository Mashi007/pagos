# backend/app/db/init_db.py
from sqlalchemy import text
from app.db.session import engine, SessionLocal, Base
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)


def check_database_connection() -> bool:
    try:
        db = SessionLocal()
        result = db.execute(text("SELECT 1"))
        result.fetchone()
        db.close()
        logger.info("✅ Conexión a la base de datos exitosa")
        return True
    except Exception as e:
        logger.error(f"❌ Error conectando a la base de datos: {str(e)}")
        return False


def create_schema():
    try:
        db = SessionLocal()
        db.execute(text("CREATE SCHEMA IF NOT EXISTS pagos_sistema"))
        db.commit()
        db.close()
        logger.info("✅ Schema 'pagos_sistema' verificado/creado")
        return True
    except Exception as e:
        logger.error(f"❌ Error creando schema: {str(e)}")
        return False


def drop_tables():
    """Elimina TODAS las tablas - FORZADO"""
    try:
        db = SessionLocal()
        logger.info("🗑️  FORZANDO eliminación de tablas...")
        
        # Eliminar en orden inverso de dependencias
        tables = [
            "pagos",
            "prestamos", 
            "notificaciones",
            "aprobaciones",
            "auditorias",
            "clientes",
            "users"
        ]
        
        for table in tables:
            try:
                db.execute(text(f"DROP TABLE IF EXISTS pagos_sistema.{table} CASCADE"))
                logger.info(f"  ✅ Eliminada: {table}")
            except Exception as e:
                logger.warning(f"  ⚠️  No se pudo eliminar {table}: {e}")
        
        db.commit()
        db.close()
        logger.info("✅ Todas las tablas eliminadas")
        return True
    except Exception as e:
        logger.error(f"❌ Error eliminando tablas: {str(e)}")
        return False


def init_database() -> bool:
    try:
        settings = get_settings()
        
        # PASO 1: Crear schema
        logger.info("🔄 Verificando schema...")
        if not create_schema():
            return False
        
        # PASO 2: FORZAR eliminación si está activado
        if settings.FORCE_RECREATE_TABLES:
            logger.info("⚠️  FORCE_RECREATE_TABLES=true - Eliminando tablas...")
            drop_tables()
        
        # PASO 3: Crear tablas
        logger.info("🔄 Creando tablas con nueva estructura...")
        
        # Importar modelos
        from app.models.cliente import Cliente
        from app.models.prestamo import Prestamo
        from app.models.pago import Pago
        from app.models.user import User
        from app.models.auditoria import Auditoria
        from app.models.notificacion import Notificacion
        from app.models.aprobacion import Aprobacion
        
        # Crear todas las tablas
        Base.metadata.create_all(bind=engine)
        
        logger.info("✅ Tablas creadas exitosamente")
        logger.info(f"📊 Total de tablas: {len(Base.metadata.tables)}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error inicializando base de datos: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def create_tables():
    try:
        create_schema()
        
        from app.models.cliente import Cliente
        from app.models.prestamo import Prestamo
        from app.models.pago import Pago
        from app.models.user import User
        from app.models.auditoria import Auditoria
        from app.models.notificacion import Notificacion
        from app.models.aprobacion import Aprobacion
        
        Base.metadata.create_all(bind=engine)
        return True
    except Exception as e:
        print(f"Error creando tablas: {str(e)}")
        return False
