# backend/app/db/init_db.py
from sqlalchemy import text, inspect
from app.db.session import engine, Base, SessionLocal
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


def check_database_connection() -> bool:
    """
    Verifica si la conexión a la base de datos está funcionando
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"❌ Error conectando a base de datos: {e}")
        return False


def table_exists(table_name: str) -> bool:
    """
    Verifica si una tabla existe en la base de datos
    """
    try:
        inspector = inspect(engine)
        return table_name in inspector.get_table_names()
    except Exception as e:
        logger.error(f"❌ Error verificando tabla {table_name}: {e}")
        return False


def create_tables():
    """
    Crea todas las tablas definidas en los modelos
    """
    try:
        # Importar todos los modelos para que SQLAlchemy los registre
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
        return True
    except Exception as e:
        logger.error(f"❌ Error creando tablas: {e}")
        return False


def init_database():
    """
    Inicializa la base de datos creando las tablas si no existen
    
    En producción, solo crea tablas que no existan.
    En desarrollo, puedes forzar recreación con la variable FORCE_RECREATE_TABLES.
    """
    try:
        logger.info("🔄 Inicializando base de datos...")
        
        # Verificar conexión primero
        if not check_database_connection():
            logger.error("❌ No se pudo conectar a la base de datos")
            return False
        
        # Verificar si las tablas principales existen
        main_tables = ["users", "clientes", "prestamos", "pagos"]
        tables_exist = all(table_exists(table) for table in main_tables)
        
        if not tables_exist:
            logger.info("📝 Tablas no encontradas, creando...")
            if create_tables():
                logger.info("✅ Base de datos inicializada correctamente")
                return True
            else:
                logger.error("❌ Error al crear tablas")
                return False
        else:
            logger.info("✅ Base de datos ya inicializada, tablas existentes")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error inicializando base de datos: {e}")
        return False


def init_db_startup():
    """
    Función que se llama al inicio de la aplicación (startup event)
    
    - En producción: Solo verifica y crea tablas si no existen
    - No hace cambios destructivos
    """
    try:
        logger.info("\n" + "="*50)
        logger.info(f"🚀 Sistema de Préstamos y Cobranza v{settings.APP_VERSION}")
        logger.info("="*50)
        logger.info(f"🗄️  Base de datos: {settings.get_database_url(hide_password=True)}")
        
        # Inicializar base de datos
        if init_database():
            # Verificar conexión
            if check_database_connection():
                logger.info("✅ Conexión a base de datos verificada")
            else:
                logger.warning("⚠️  Advertencia: Problema de conexión a base de datos")
        else:
            logger.warning("⚠️  Advertencia: Error inicializando tablas")
        
        logger.info(f"🌍 Entorno: {settings.ENVIRONMENT}")
        logger.info("📝 Documentación: /docs")
        logger.info(f"🔧 Debug mode: {'ON' if settings.DEBUG else 'OFF'}")
        logger.info("="*50)
        logger.info("")
        
    except Exception as e:
        logger.error(f"❌ Error en startup de DB: {e}")
        # No lanzar excepción para que la app siga funcionando
        # aunque la DB tenga problemas


def init_db_shutdown():
    """
    Función que se llama al cerrar la aplicación (shutdown event)
    """
    try:
        from app.db.session import close_db_connections
        close_db_connections()
        logger.info("")
        logger.info("🛑 Sistema de Préstamos y Cobranza detenido")
    except Exception as e:
        logger.error(f"❌ Error en shutdown de DB: {e}")
