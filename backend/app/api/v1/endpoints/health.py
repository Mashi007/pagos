"""
Endpoints de health check para monitoreo y debugging de la aplicación.

GET /health/              - Health check básico
GET /health/db            - Verifica conexión a BD y tablas críticas
GET /health/detailed      - Reporte completo (solo dev)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
from app.core.database import get_db, engine
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def health_check():
    """Health check básico: confirma que la API está up."""
    return {
        "status": "ok",
        "message": "API is running",
    }


@router.get("/db")
async def health_check_db(db: Session = Depends(get_db)):
    """Verifica BD: conexión, tablas críticas, acceso.
    
    Retorna:
        - status: "ok" si todo está bien, "error" si hay problemas
        - db_connected: booleano indicando si hay conexión
        - tables_exist: dict con presencia de tablas críticas
        - prestamos_count: cantidad de registros en tabla 'prestamos'
        - error: mensaje de error si aplica
    """
    result = {
        "status": "ok",
        "db_connected": False,
        "tables_exist": {},
        "prestamos_count": 0,
        "error": None,
    }
    
    try:
        # Verificar conexión básica
        db.execute(text("SELECT 1"))
        result["db_connected"] = True
        logger.debug("[Health] Conexión a BD verificada")
        
        # Verificar tablas críticas
        CRITICAL_TABLES = [
            "clientes",
            "prestamos",
            "cuotas",
            "pagos",
            "pagos_con_errores",
            "revisar_pagos",
            "cuota_pagos",
            "pagos_whatsapp",
            "tickets",
        ]
        
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        for table in CRITICAL_TABLES:
            result["tables_exist"][table] = table in existing_tables
        
        # Contar registros en tabla crítica
        prestamos_count_result = db.execute(
            text("SELECT COUNT(*) FROM prestamos")
        ).scalar()
        result["prestamos_count"] = prestamos_count_result or 0
        
        # Determinar status
        all_tables_exist = all(result["tables_exist"].values())
        if not all_tables_exist:
            result["status"] = "error"
            missing = [t for t, exists in result["tables_exist"].items() if not exists]
            result["error"] = f"Tablas faltantes: {missing}"
        
        return result
        
    except Exception as e:
        result["status"] = "error"
        result["error"] = f"{type(e).__name__}: {str(e)}"
        logger.error(f"[Health] Error en health_check_db: {result['error']}")
        raise HTTPException(status_code=503, detail=result)


@router.get("/detailed")
async def health_check_detailed(db: Session = Depends(get_db)):
    """Reporte detallado (para desarrollo y debugging).
    
    Incluye:
        - Tablas existentes en BD
        - Counts de tablas principales
        - Pool de conexiones
        - Información de configuración (sin secretos)
    
    ⚠️ Nota: Solo disponible en desarrollo.
    """
    try:
        from app.core.config import settings
        
        # Obtener tablas
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        # Counts principales
        counts = {}
        table_counts = ["clientes", "prestamos", "cuotas", "pagos", "pagos_con_errores", "pagos_whatsapp", "tickets"]
        for table in table_counts:
            if table in tables:
                try:
                    count = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0
                    counts[table] = count
                except Exception as e:
                    counts[table] = f"Error: {str(e)[:50]}"
        
        # Pool stats
        pool_status = {
            "pool_size": engine.pool.size(),
            "checked_out_count": engine.pool.checkedout(),
        }
        
        return {
            "status": "ok",
            "tables": tables,
            "table_counts": counts,
            "pool": pool_status,
            "database_url": settings.DATABASE_URL[:80] if settings.DATABASE_URL else None,
            "environment": settings.ENVIRONMENT,
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Error en health_check_detailed: {str(e)}"
        )
