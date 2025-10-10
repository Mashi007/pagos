# backend/app/api/v1/endpoints/health.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db, Base, engine
from app.db.init_db import check_database_connection
from app.config import get_settings
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    settings = get_settings()
    db_status = check_database_connection()
    
    return {
        "status": "healthy" if db_status else "unhealthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database": "connected" if db_status else "disconnected",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/test/init-db")
async def initialize_database(db: Session = Depends(get_db)):
    """
    Endpoint para RECREAR la base de datos
    ⚠️ ELIMINA todas las tablas y las vuelve a crear
    """
    try:
        # PASO 1: Eliminar tablas
        logger.info("🗑️  Eliminando tablas...")
        
        tables_to_drop = [
            "pagos",
            "prestamos",
            "notificaciones",
            "aprobaciones",
            "auditorias",
            "clientes",
            "users"
        ]
        
        for table in tables_to_drop:
            try:
                db.execute(text(f"DROP TABLE IF EXISTS pagos_sistema.{table} CASCADE"))
                logger.info(f"  ✅ Eliminada: {table}")
            except Exception as e:
                logger.warning(f"  ⚠️  Error eliminando {table}: {e}")
        
        db.commit()
        logger.info("✅ Tablas eliminadas")
        
        # PASO 2: Recrear tablas
        logger.info("🔄 Recreando tablas...")
        
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
        
        logger.info("✅ Tablas recreadas exitosamente")
        
        return {
            "status": "success",
            "message": "✅ Base de datos recreada exitosamente",
            "tables_dropped": len(tables_to_drop),
            "tables_created": len(Base.metadata.tables)
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error: {str(e)}")
        return {
            "status": "error",
            "message": f"❌ Error: {str(e)}"
        }
