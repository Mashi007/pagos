# backend/app/api/v1/endpoints/diagnostico.py
"""
Endpoint de diagnóstico para verificar el estado del sistema
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db, engine
from app.core.config import settings
import logging
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/diagnostico/sistema")
async def diagnostico_sistema():
    """
    Diagnóstico completo del sistema sin requerir base de datos
    """
    try:
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "database_url_configured": bool(settings.DATABASE_URL),
            "database_url_length": len(settings.DATABASE_URL) if settings.DATABASE_URL else 0,
            "secret_key_configured": bool(settings.SECRET_KEY),
            "api_prefix": settings.API_V1_PREFIX,
            "cors_origins": settings.ALLOWED_ORIGINS,
            "pool_size": settings.DB_POOL_SIZE,
            "pool_timeout": settings.DB_POOL_TIMEOUT
        }
    except Exception as e:
        logger.error(f"Error en diagnóstico: {e}")
        raise HTTPException(status_code=500, detail=f"Error en diagnóstico: {str(e)}")

@router.get("/diagnostico/database")
async def diagnostico_database(db: Session = Depends(get_db)):
    """
    Diagnóstico específico de la base de datos
    """
    try:
        # Test de conexión básica
        result = db.execute(text("SELECT 1 as test"))
        test_result = result.fetchone()
        
        # Verificar tablas
        tables_result = db.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        tables = [row[0] for row in tables_result.fetchall()]
        
        # Verificar usuarios
        try:
            users_result = db.execute(text("SELECT COUNT(*) FROM users"))
            user_count = users_result.fetchone()[0]
        except:
            user_count = "Error"
        
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "database_connection": "ok",
            "test_query_result": test_result[0] if test_result else None,
            "tables_count": len(tables),
            "tables": tables,
            "users_count": user_count,
            "database_url": settings.DATABASE_URL[:50] + "..." if settings.DATABASE_URL else None
        }
        
    except Exception as e:
        logger.error(f"Error en diagnóstico de DB: {e}")
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "database_connection": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }

@router.get("/diagnostico/endpoints")
async def diagnostico_endpoints():
    """
    Lista todos los endpoints disponibles
    """
    try:
        from app.main import app
        
        endpoints = []
        for route in app.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                endpoints.append({
                    "path": route.path,
                    "methods": list(route.methods),
                    "name": getattr(route, 'name', 'N/A')
                })
        
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "total_endpoints": len(endpoints),
            "endpoints": endpoints
        }
        
    except Exception as e:
        logger.error(f"Error listando endpoints: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
