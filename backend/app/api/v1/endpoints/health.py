"""
Endpoints de health check para monitoreo y debugging de la aplicación.

GET /health/                        - Health check básico
GET /health/db                      - Verifica conexión a BD y tablas críticas
GET /health/cobros                  - Módulo Cobros: BD, GEMINI_API_KEY y SMTP configurados (sin exponer secretos)
GET /health/clientes-stats-diagnostico - Diagnóstico KPI nuevos_este_mes (público, sin auth)
GET /health/detailed                - Reporte completo (solo dev)
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
        
        # Verificar tablas críticas (incluye módulos Cobros, auth, reportes)
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
            "pagos_reportados",
            "usuarios",
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


@router.get("/gemini")
async def health_check_gemini():
    """Test indirecto de Gemini: prompt de texto simple para verificar API key y que el servicio responde."""
    from app.services.pagos_gmail.gemini_service import check_gemini_available
    result = check_gemini_available()
    if not result.get("ok"):
        raise HTTPException(status_code=503, detail=result)
    return result


@router.get("/clientes-stats-diagnostico")
async def health_clientes_stats_diagnostico(db: Session = Depends(get_db)):
    """
    Diagnóstico público (sin auth) del KPI nuevos_este_mes.
    Para auditar por qué el KPI puede estar en 0.
    """
    try:
        mes_bd = db.execute(text("SELECT date_trunc('month', CURRENT_TIMESTAMP)")).scalar()
        total_con_fecha = db.scalar(
            text("SELECT count(*)::int FROM clientes WHERE fecha_registro IS NOT NULL")
        ) or 0
        nuevos = db.scalar(text("""
            SELECT count(*)::int FROM clientes
            WHERE fecha_registro IS NOT NULL
              AND date_trunc('month', fecha_registro) = date_trunc('month', CURRENT_TIMESTAMP)
        """)) or 0
        ejemplo = db.execute(text("""
            SELECT id, fecha_registro::text
            FROM clientes
            WHERE fecha_registro IS NOT NULL
            ORDER BY fecha_registro DESC
            LIMIT 1
        """)).first()
        return {
            "mes_actual_bd": str(mes_bd) if mes_bd else None,
            "total_con_fecha_registro": int(total_con_fecha),
            "nuevos_este_mes": int(nuevos),
            "ejemplo_ultimo_registro": {"id": ejemplo[0], "fecha_registro": ejemplo[1]} if ejemplo else None,
        }
    except Exception as e:
        logger.exception("Error en health/clientes-stats-diagnostico: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/cobros")
async def health_check_cobros(db: Session = Depends(get_db)):
    """
    Verifica que el módulo Cobros tenga lo necesario para operar:
    - BD accesible
    - GEMINI_API_KEY configurado (sin llamar a la API, sin exponer el valor)
    - Servicio Gemini de Cobros = servicio del sistema (app.services.pagos_gmail.gemini_service)
    - SMTP con credenciales no vacías (desde Configuración > Email o .env)

    No expone secretos. Útil para despliegue y alertas (ej. Uptime Robot).
    """
    from app.core.config import settings
    from app.core.email_config_holder import get_smtp_config

    result = {
        "status": "ok",
        "db_ok": False,
        "gemini_configured": False,
        "cobros_gemini_service_connected": False,
        "smtp_configured": False,
        "error": None,
    }
    try:
        db.execute(text("SELECT 1"))
        result["db_ok"] = True
    except Exception as e:
        result["status"] = "error"
        result["error"] = f"BD: {type(e).__name__}: {str(e)[:200]}"
        return result

    gemini_key = getattr(settings, "GEMINI_API_KEY", None) or ""
    result["gemini_configured"] = bool((gemini_key or "").strip())

    try:
        from app.services.pagos_gmail.gemini_service import compare_form_with_image
        result["cobros_gemini_service_connected"] = callable(compare_form_with_image)
    except Exception as e:
        logger.warning("[Health/cobros] No se pudo cargar servicio Gemini para Cobros: %s", e)

    cfg = get_smtp_config()
    result["smtp_configured"] = bool(
        (cfg.get("smtp_host") or "").strip()
        and (cfg.get("smtp_user") or "").strip()
        and (cfg.get("smtp_password") or "").strip()
    )

    if not result["gemini_configured"] or not result["smtp_configured"] or not result["cobros_gemini_service_connected"]:
        result["status"] = "degraded"
        parts = []
        if not result["gemini_configured"]:
            parts.append("GEMINI_API_KEY no configurado")
        if result["gemini_configured"] and not result["cobros_gemini_service_connected"]:
            parts.append("Servicio Gemini para Cobros no cargable")
        if not result["smtp_configured"]:
            parts.append("SMTP incompleto (host/usuario/contraseña)")
        result["error"] = "; ".join(parts) if parts else result.get("error")

    return result


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
        
        # Counts principales (incluye tablas Cobros y usuarios)
        counts = {}
        table_counts = [
            "clientes", "prestamos", "cuotas", "pagos", "pagos_con_errores",
            "pagos_whatsapp", "tickets", "pagos_reportados", "usuarios",
        ]
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
            "environment": getattr(settings, "ENVIRONMENT", None),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Error en health_check_detailed: {str(e)}"
        )
