# backend/app/api/v1/endpoints/health.py
"""Health Checks con Análisis de Impacto en Performance

Implementa monitoreo de salud del sistema con análisis de impacto
"""

import logging
import time
from typing import Any, Dict

import psutil
from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.core.config import settings
from app.core.performance_monitor import performance_monitor
from app.db.session import engine

# Constantes de configuración
CACHE_DURATION_SECONDS = 30
HEALTH_CHECK_TIMEOUT = 5
MAX_RESPONSE_TIME_MS = 100
CPU_THRESHOLD_PERCENT = 80
MEMORY_THRESHOLD_PERCENT = 85
DISK_THRESHOLD_PERCENT = 90

# Tablas críticas para verificar
CRITICAL_TABLES = [
    # "aprobaciones",  # MODULO APROBACIONES DESHABILITADO
    "auditorias",
    "clientes",
    "users",
]

router = APIRouter()
logger = logging.getLogger(__name__)

# Cache para métricas del sistema
_last_system_check = {"timestamp": 0, "data": {}}
_last_db_check = {"timestamp": 0, "data": {}, "cache_duration": CACHE_DURATION_SECONDS}


def get_system_metrics() -> Dict[str, Any]:
    """Obtiene métricas del sistema para análisis de impacto"""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_gb": memory.available / (1024**3),
            "disk_percent": disk.percent,
            "disk_free_gb": disk.free / (1024**3),
        }
    except Exception as e:
        logger.warning(f"Error obteniendo métricas del sistema: {e}")
        return {
            "cpu_percent": 0,
            "memory_percent": 0,
            "memory_available_gb": 0,
            "disk_percent": 0,
            "disk_free_gb": 0,
        }


def check_database_cached() -> Dict[str, Any]:
    """Verifica la DB con cache para reducir carga y análisis de impacto"""
    current_time = time.time()

    if current_time - _last_db_check["timestamp"] < _last_db_check["cache_duration"]:
        return _last_db_check["data"]

    try:
        from app.db.init_db import check_database_connection

        db_status = check_database_connection()

        _last_db_check["data"] = {
            "status": db_status,
            "timestamp": current_time,
        }
        _last_db_check["timestamp"] = current_time

        return _last_db_check["data"]
    except Exception as e:
        logger.error(f"Error verificando DB: {e}")
        return {"status": False, "error": str(e)}


@router.get("/cors-debug")
async def cors_debug():
    """Endpoint para debuggear CORS"""
    return {
        "message": "CORS debug endpoint",
        "origin": "allowed",
        "methods": ["GET", "POST", "PUT", "DELETE"],
    }


@router.get("/health/render")
@router.head("/health/render")
async def render_health_check():
    """Health check optimizado para Render

    - Respuesta ultra rápida
    - Acepta tanto GET como HEAD
    - Sin verificaciones de DB para evitar timeouts
    """
    return Response(
        content='{"status": "healthy", "service": "pagos-api"}',
        status_code=status.HTTP_200_OK,
        media_type="application/json",
    )


@router.get("/health")
async def detailed_health_check(response: Response):
    """Health check detallado con análisis de impacto en performance

    - Verifica DB con métricas de respuesta
    - Incluye métricas del sistema
    - Análisis de impacto en performance
    """
    start_time = time.time()

    try:
        # Obtener métricas del sistema
        system_metrics = get_system_metrics()

        # Verificar DB con cache
        db_check = check_database_cached()

        # Calcular tiempo total de respuesta
        response_time_ms = (time.time() - start_time) * 1000

        # Análisis de impacto
        impact_analysis = {
            "response_time_ms": response_time_ms,
            "performance_impact": "low",
            "alerts": [],
        }

        # Verificar umbrales de performance
        if system_metrics["cpu_percent"] > CPU_THRESHOLD_PERCENT:
            impact_analysis["alerts"].append(
                {
                    "type": "cpu_high",
                    "message": (
                        f"CPU usage {system_metrics['cpu_percent']:.1f}% " f"exceeds threshold {CPU_THRESHOLD_PERCENT}%"
                    ),
                    "severity": "WARNING",
                }
            )

        if system_metrics["memory_percent"] > MEMORY_THRESHOLD_PERCENT:
            impact_analysis["alerts"].append(
                {
                    "type": "memory_high",
                    "message": (
                        f"Memory usage {system_metrics['memory_percent']:.1f}% "
                        f"exceeds threshold {MEMORY_THRESHOLD_PERCENT}%"
                    ),
                    "severity": "WARNING",
                }
            )

        if system_metrics["disk_percent"] > DISK_THRESHOLD_PERCENT:
            impact_analysis["alerts"].append(
                {
                    "type": "disk_high",
                    "message": (
                        f"Disk usage {system_metrics['disk_percent']:.1f}% " f"exceeds threshold {DISK_THRESHOLD_PERCENT}%"
                    ),
                    "severity": "CRITICAL",
                }
            )

        # Determinar estado general
        overall_status = "healthy"
        if not db_check["status"]:
            overall_status = "unhealthy"
        elif impact_analysis["response_time_ms"] > MAX_RESPONSE_TIME_MS:
            overall_status = "degraded"
        elif impact_analysis["alerts"]:
            overall_status = "warning"

        return {
            "status": overall_status,
            "timestamp": time.time(),
            "response_time_ms": response_time_ms,
            "database": db_check,
            "system_metrics": system_metrics,
            "impact_analysis": impact_analysis,
            "environment": settings.ENVIRONMENT,
            "version": settings.APP_VERSION,
        }

    except Exception as e:
        logger.error(f"Error en health check detallado: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "error",
            "message": str(e),
            "timestamp": time.time(),
        }


@router.get("/health/ready")
async def readiness_check():
    """Readiness check para Kubernetes/Docker"""
    try:
        # Verificar conexión a DB
        db_status = True
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as e:
            logger.error(f"Readiness check failed: {e}")
            db_status = False

        if not db_status:
            return Response(
                content='{"status": "not_ready", "reason": "database"}',
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                media_type="application/json",
            )

        return Response(
            content='{"status": "ready"}',
            status_code=status.HTTP_200_OK,
            media_type="application/json",
        )

    except Exception as e:
        logger.error(f"Readiness check error: {e}")
        return Response(
            content=f'{{"status": "error", "message": "{str(e)}"}}',
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type="application/json",
        )


@router.get("/health/live")
async def liveness_check():
    """Liveness check para Kubernetes/Docker"""
    return Response(
        content='{"status": "alive"}',
        status_code=status.HTTP_200_OK,
        media_type="application/json",
    )


@router.get("/performance/summary")
async def performance_summary():
    """Obtener resumen general de performance de todos los endpoints"""
    try:
        summary = performance_monitor.get_summary()
        return {
            "status": "success",
            "summary": summary,
            "timestamp": time.time(),
        }
    except Exception as e:
        logger.error(f"Error obteniendo resumen de performance: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": time.time(),
        }


@router.get("/performance/slow")
async def performance_slow_endpoints(threshold_ms: float = 1000, limit: int = 20):
    """
    Obtener endpoints lentos ordenados por tiempo promedio

    Args:
        threshold_ms: Umbral mínimo de tiempo en ms (default: 1000ms)
        limit: Número máximo de resultados (default: 20)
    """
    try:
        slow_endpoints = performance_monitor.get_slow_endpoints(threshold_ms=threshold_ms, limit=limit)

        return {
            "status": "success",
            "threshold_ms": threshold_ms,
            "count": len(slow_endpoints),
            "endpoints": slow_endpoints,
            "timestamp": time.time(),
        }
    except Exception as e:
        logger.error(f"Error obteniendo endpoints lentos: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": time.time(),
        }


@router.get("/performance/endpoint/{method}/{path:path}")
async def performance_endpoint_stats(method: str, path: str):
    """
    Obtener estadísticas detalladas de un endpoint específico

    Args:
        method: Método HTTP (GET, POST, etc.)
        path: Ruta del endpoint
    """
    try:
        stats = performance_monitor.get_endpoint_stats(method=method.upper(), path=path)

        if not stats:
            return Response(
                content='{"status": "not_found", "message": "Endpoint no encontrado en métricas"}',
                status_code=status.HTTP_404_NOT_FOUND,
                media_type="application/json",
            )

        return {
            "status": "success",
            "stats": stats,
            "timestamp": time.time(),
        }
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas de endpoint: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": time.time(),
        }


@router.get("/performance/recent")
async def performance_recent_requests(limit: int = 50):
    """
    Obtener peticiones recientes

    Args:
        limit: Número máximo de peticiones a retornar (default: 50, max: 200)
    """
    try:
        limit = min(limit, 200)  # Limitar máximo a 200
        recent = performance_monitor.get_recent_requests(limit=limit)

        return {
            "status": "success",
            "count": len(recent),
            "requests": recent,
            "timestamp": time.time(),
        }
    except Exception as e:
        logger.error(f"Error obteniendo peticiones recientes: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": time.time(),
        }
