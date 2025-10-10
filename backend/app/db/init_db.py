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


def drop_and_recreate_tables():
    """Elimina y recrea todas las tablas (solo para desarrollo)"""
    try:
        db = SessionLocal()
        
        # Eliminar tablas en orden inverso de dependencias
        logger.info("🗑️  Eliminando tablas existentes...")
        db.execute(text("DROP TABLE IF EXISTS pagos_sistema.pagos CASCADE"))
        db.execute(text("DROP TABLE IF EXISTS pagos_sistema.prestamos CASCADE"))
        db.execute(text("DROP TABLE IF EXISTS pagos_sistema.notificaciones CASCADE"))
        db.execute(text("DROP TABLE IF EXISTS pagos_sistema.aprobaciones CASCADE"))
        db.execute(text("DROP TABLE IF EXISTS pagos_sistema.auditorias CASCADE"))
        db.execute(text("DROP TABLE IF EXISTS pagos_sistema.clientes CASCADE"))
        db.execute(text("DROP TABLE IF EXISTS pagos_sistema.users CASCADE"))
        db.commit()
        db.close()
        
        logger.info("✅ Tablas eliminadas")
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
            logger.error("❌ No se pudo crear el schema")
            return False
        
        # PASO 2: Eliminar tablas viejas (TEMPORAL - solo en desarrollo)
        if settings.ENVIRONMENT != "production":
            drop_and_recreate_tables()
        
        # PASO 3: Crear tablas
        logger.info("🔄 Iniciando creación de tablas...")
        
        # Importar modelos
        from app.models.cliente import Cliente
        from app.models.prestamo import Prestamo
        from app.models.pago import Pago
        from app.models.user import User
        from app.models.auditoria import Auditoria
        from app.models.notificacion import Notificacion
        from app.models.aprobacion import Aprobacion
        
        # Crear tablas
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
