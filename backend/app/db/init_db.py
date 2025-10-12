import logging
import os
from sqlalchemy import create_engine, text
from .models import Base
from .config import engine, test_connection

logger = logging.getLogger(__name__)

def init_db():
    """Inicializa la base de datos"""
    logger.info("")
    logger.info("=" * 50)
    logger.info("🚀 Sistema de Préstamos y Cobranza v1.0.0")
    logger.info("=" * 50)
    
    # Mostrar información de la base de datos (ocultar contraseña)
    db_url = os.getenv("DATABASE_URL", "No configurada")
    if "://" in db_url:
        # Ocultar contraseña en los logs
        parts = db_url.split("://")[1].split("@")
        if len(parts) > 1:
            user_pass = parts[0].split(":")
            if len(user_pass) > 1:
                safe_url = f"{db_url.split('://')[0]}://{user_pass[0]}:***@{parts[1]}"
            else:
                safe_url = db_url
        else:
            safe_url = db_url
    else:
        safe_url = db_url
    
    logger.info(f"🗄️  Base de datos: {safe_url}")
    logger.info("🔄 Inicializando base de datos...")
    
    try:
        # Probar conexión primero
        if not test_connection():
            logger.error("❌ No se pudo conectar a la base de datos")
            logger.warning("⚠️  Advertencia: Error inicializando tablas")
        else:
            # Si la conexión es exitosa, crear tablas
            Base.metadata.create_all(bind=engine)
            logger.info("✅ Tablas creadas/verificadas exitosamente")
        
    except Exception as e:
        logger.error(f"❌ Error conectando a base de datos: {e}")
        logger.error("❌ No se pudo conectar a la base de datos")
        logger.warning("⚠️  Advertencia: Error inicializando tablas")
    
    # Información del entorno
    env = os.getenv("ENVIRONMENT", "development")
    logger.info(f"🌍 Entorno: {env}")
    logger.info("📝 Documentación: /docs")
    debug_mode = os.getenv("DEBUG", "false").lower() == "true"
    logger.info(f"🔧 Debug mode: {'ON' if debug_mode else 'OFF'}")
    logger.info("=" * 50)
    logger.info("")

def shutdown_db():
    """Cierra las conexiones de la base de datos"""
    logger.info("")
    logger.info("🛑 Sistema de Préstamos y Cobranza detenido")
    engine.dispose()