"""
Endpoints de Monitoreo y Debugging
Proporciona métricas, alertas y herramientas de debugging
"""

import logging
import time
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user, get_db
from app.core.performance_monitor import performance_monitor
from app.models.user import User
from app.utils.db_analyzer import (
    analyze_query_tables_columns,
    get_database_info,
    get_database_size,
    get_indexes_for_table,
    get_table_columns,
    get_table_sizes,
)
from app.utils.query_monitor import query_monitor

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/queries/slow")
def get_slow_queries(
    threshold_ms: float = Query(1000, description="Umbral mínimo en ms"),
    limit: int = Query(20, description="Número máximo de resultados"),
    db = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener queries lentas ordenadas por tiempo promedio
    
    Útil para identificar queries que necesitan optimización
    """
    try:
        slow_queries = query_monitor.get_slow_queries(threshold_ms=threshold_ms, limit=limit)
        
        return {
            "status": "success",
            "threshold_ms": threshold_ms,
            "count": len(slow_queries),
            "queries": slow_queries,
            "timestamp": time.time(),
        }
    except Exception as e:
        logger.error(f"Error obteniendo queries lentas: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": time.time(),
        }


@router.get("/queries/stats/{query_name}")
def get_query_stats(
    query_name: str,
    db = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener estadísticas detalladas de una query específica
    """
    try:
        stats = query_monitor.get_query_stats(query_name)
        
        if not stats:
            return {
                "status": "not_found",
                "message": f"Query '{query_name}' no encontrada",
                "timestamp": time.time(),
            }
        
        return {
            "status": "success",
            "query_name": query_name,
            "stats": stats,
            "timestamp": time.time(),
        }
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas de query: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": time.time(),
        }


@router.get("/queries/summary")
def get_queries_summary(
    db = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Resumen general de todas las queries monitoreadas
    """
    try:
        summary = query_monitor.get_summary()
        
        return {
            "status": "success",
            "summary": summary,
            "timestamp": time.time(),
        }
    except Exception as e:
        logger.error(f"Error obteniendo resumen de queries: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": time.time(),
        }


@router.get("/alerts/recent")
def get_recent_alerts(
    limit: int = Query(50, description="Número máximo de alertas"),
    severity: Optional[str] = Query(None, description="Filtrar por severidad: CRITICAL, HIGH, MEDIUM"),
    db = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener alertas recientes de queries
    
    Útil para identificar problemas en tiempo real
    """
    try:
        alerts = query_monitor.get_recent_alerts(limit=limit)
        
        # Filtrar por severidad si se especifica
        if severity:
            alerts = [a for a in alerts if a.get("severity") == severity.upper()]
        
        return {
            "status": "success",
            "count": len(alerts),
            "alerts": alerts,
            "timestamp": time.time(),
        }
    except Exception as e:
        logger.error(f"Error obteniendo alertas: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": time.time(),
        }


@router.get("/dashboard/performance")
def get_dashboard_performance(
    db = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Métricas de rendimiento del dashboard
    
    Combina métricas de endpoints, queries e información de BD
    """
    try:
        # Obtener métricas de endpoints
        endpoint_summary = performance_monitor.get_summary()
        slow_endpoints = performance_monitor.get_slow_endpoints(threshold_ms=2000, limit=10)
        
        # Obtener métricas de queries
        query_summary = query_monitor.get_summary()
        slow_queries = query_monitor.get_slow_queries(threshold_ms=1000, limit=10)
        
        # Obtener alertas recientes
        recent_alerts = query_monitor.get_recent_alerts(limit=20)
        critical_alerts = [a for a in recent_alerts if a.get("severity") == "CRITICAL"]
        high_alerts = [a for a in recent_alerts if a.get("severity") == "HIGH"]
        
        # Obtener información de BD
        db_info = get_database_info(db)
        
        return {
            "status": "success",
            "endpoints": {
                "summary": endpoint_summary,
                "slow_endpoints": slow_endpoints,
            },
            "queries": {
                "summary": query_summary,
                "slow_queries": slow_queries,
            },
            "database": db_info,
            "alerts": {
                "total": len(recent_alerts),
                "critical": len(critical_alerts),
                "high": len(high_alerts),
                "recent": recent_alerts[:10],  # Últimas 10
            },
            "timestamp": time.time(),
        }
    except Exception as e:
        logger.error(f"Error obteniendo métricas de dashboard: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": time.time(),
        }


@router.get("/database/info")
def get_database_information(
    db = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Información completa de la base de datos
    
    Incluye tamaño, tablas, índices y columnas
    """
    try:
        db_info = get_database_info(db)
        
        return {
            "status": "success",
            "database": db_info,
            "timestamp": time.time(),
        }
    except Exception as e:
        logger.error(f"Error obteniendo información de BD: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": time.time(),
        }


@router.get("/database/tables/{table_name}/columns")
def get_table_columns_info(
    table_name: str,
    db = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener columnas de una tabla específica
    """
    try:
        columns = get_table_columns(db, table_name)
        
        return {
            "status": "success",
            "table_name": table_name,
            "columns": columns,
            "count": len(columns),
            "timestamp": time.time(),
        }
    except Exception as e:
        logger.error(f"Error obteniendo columnas de tabla {table_name}: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": time.time(),
        }


@router.get("/database/tables/{table_name}/indexes")
def get_table_indexes_info(
    table_name: str,
    db = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener índices de una tabla específica
    """
    try:
        indexes = get_indexes_for_table(db, table_name)
        
        return {
            "status": "success",
            "table_name": table_name,
            "indexes": indexes,
            "count": len(indexes),
            "timestamp": time.time(),
        }
    except Exception as e:
        logger.error(f"Error obteniendo índices de tabla {table_name}: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": time.time(),
        }

