# app/db/init_db.py
from sqlalchemy import text
from app.db.session import engine, SessionLocal, Base  # ✅ Importar Base directo
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)


def check_database_connection() -> bool:
    """
    Verifica si la conexión a la base de datos está funcionando
    
    Returns:
        bool: True si la conexión es exitosa, False en caso contrario
    """
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


def init_database() -> bool:
    """
    Inicializa la base de datos creando todas las tablas
    
    Returns:
        bool: True si la inicialización fue exitosa
    """
    try:
        settings = get_settings()
        
        logger.info("🔄 Iniciando creación de tablas...")
        
        # ✅ CRÍTICO: Importar modelos AQUÍ DENTRO (lazy loading)
        # Esto evita el ciclo circular durante el startup
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
    """
    Función auxiliar para crear tablas (sin logging extensivo)
    """
    try:
        # ✅ Importar modelos dentro de la función
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
