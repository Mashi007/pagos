# backend/app/api/v1/endpoints/health.py
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db, Base, engine
from app.core.config import get_settings  # ✅ CORREGIDO
from datetime import datetime, timedelta
import logging
from typing import Dict, Any
import asyncio

router = APIRouter()
logger = logging.getLogger(__name__)

# Cache para evitar múltiples checks de DB
_last_db_check: Dict[str, Any] = {
    "timestamp": None,
    "status": True,
    "cache_duration": 30  # segundos
}


def check_database_cached() -> bool:
    """
    Verifica la DB con cache para reducir carga
    Solo hace check real cada 30 segundos
    """
    global _last_db_check
    
    now = datetime.utcnow()
    
    # Si no hay cache o expiró, hacer check real
    if (_last_db_check["timestamp"] is None or 
        (now - _last_db_check["timestamp"]).total_seconds() > _last_db_check["cache_duration"]):
        
        try:
            from app.db.init_db import check_database_connection
            db_status = check_database_connection()
            
            _last_db_check.update({
                "timestamp": now,
                "status": db_status
            })
            logger.info(f"🔍 DB Check realizado: {db_status}")
        except Exception as e:
            logger.error(f"❌ Error en DB check: {e}")
            _last_db_check.update({
                "timestamp": now,
                "status": False
            })
    
    return _last_db_check["status"]


@router.get("/cors-debug")
async def cors_debug():
    """Endpoint para debuggear CORS"""
    from app.core.config import settings
    return {
        "cors_origins": settings.CORS_ORIGINS,
        "cors_origins_type": str(type(settings.CORS_ORIGINS)),
        "cors_origins_list": list(settings.CORS_ORIGINS),
        "environment": settings.ENVIRONMENT,
        "message": "CORS Debug Info"
    }

@router.get("/health/render")
@router.head("/health/render")
async def render_health_check():
    """
    Health check optimizado para Render
    
    - Respuesta ultra rápida
    - Acepta tanto GET como HEAD
    - Sin verificaciones de DB para evitar timeouts
    - Ideal para health checks frecuentes de Render
    """
    return {
        "status": "ok",
        "service": "pagos-backend",
        "timestamp": datetime.utcnow().isoformat(),
        "render_optimized": True
    }


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(response: Response):
    """
    Health check LIGERO para Railway
    
    - No verifica DB por defecto (Railway lo llama cada ~5 segundos)
    - Responde inmediatamente con status 200
    - Útil para keep-alive y load balancers
    """
    settings = get_settings()
    
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/health/full", status_code=status.HTTP_200_OK)
async def health_check_full(response: Response):
    """
    Health check COMPLETO con verificación de DB
    
    - Usa cache de 30 segundos para reducir carga
    - Verifica conectividad real a base de datos
    - Usar para monitoreo menos frecuente
    """
    settings = get_settings()
    
    # Check con cache
    db_status = check_database_cached()
    
    # Si DB está caída, devolver 503
    if not db_status:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unhealthy",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "database": "disconnected",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database": "connected",
        "database_last_check": _last_db_check["timestamp"].isoformat() if _last_db_check["timestamp"] else None,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/health/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """
    Readiness probe - verifica que la app esté lista para recibir tráfico
    
    - Verifica DB en tiempo real
    - Puede ser más lento
    - Usar para Kubernetes readiness probes o checks iniciales
    """
    settings = get_settings()
    
    try:
        # Check real de DB
        db.execute(text("SELECT 1"))
        db_status = True
    except Exception as e:
        logger.error(f"❌ Readiness check failed: {e}")
        db_status = False
    
    if not db_status:
        return Response(
            content='{"status": "not_ready"}',
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type="application/json"
        )
    
    return {
        "status": "ready",
        "app": settings.APP_NAME,
        "database": "connected",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/health/live")
async def liveness_check():
    """
    Liveness probe - verifica que la app esté viva (no colgada)
    
    - Respuesta instantánea
    - No hace checks externos
    - Usar para Kubernetes liveness probes
    """
    return {
        "status": "alive",
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
        
        # Invalidar cache de DB check
        global _last_db_check
        _last_db_check["timestamp"] = None
        
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
