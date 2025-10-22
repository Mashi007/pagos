# backend/app/api/v1/endpoints/health.py
"""
Health Checks con Análisis de Impacto en Performance
Implementa monitoreo de salud del sistema con métricas de impacto
"""
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db, Base, engine
from app.core.config import get_settings
from datetime import datetime, timedelta
import logging
from typing import Dict, Any
import asyncio
import time
import psutil
import os

# Constantes de configuración
CACHE_DURATION_SECONDS = 30
HEALTH_CHECK_TIMEOUT = 5
MAX_RESPONSE_TIME_MS = 100
CPU_THRESHOLD_PERCENT = 80
MEMORY_THRESHOLD_PERCENT = 85
DISK_THRESHOLD_PERCENT = 90

TABLES_TO_DROP = [
    "pagos",
    "prestamos", 
    "notificaciones",
    "aprobaciones",
    "auditorias",
    "clientes",
    "users"
]

router = APIRouter()
logger = logging.getLogger(__name__)

# Cache para health checks con métricas de impacto
_last_db_check: Dict[str, Any] = {
    "timestamp": None,
    "status": True,
    "cache_duration": CACHE_DURATION_SECONDS,
    "response_time_ms": 0,
    "cpu_usage": 0,
    "memory_usage": 0
}


def get_system_metrics() -> Dict[str, Any]:
    """
    Obtiene métricas del sistema para análisis de impacto
    """
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_mb": memory.available // (1024 * 1024),
            "disk_percent": disk.percent,
            "disk_free_gb": disk.free // (1024 * 1024 * 1024),
            "process_count": len(psutil.pids()),
            "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
        }
    except Exception as e:
        logger.warning(f"Error obteniendo métricas del sistema: {e}")
        return {
            "cpu_percent": 0,
            "memory_percent": 0,
            "memory_available_mb": 0,
            "disk_percent": 0,
            "disk_free_gb": 0,
            "process_count": 0,
            "load_average": [0, 0, 0]
        }


def check_database_cached() -> Dict[str, Any]:
    """
    Verifica la DB con cache para reducir carga y análisis de impacto
    Solo hace check real cada 30 segundos
    """
    start_time = time.time()
    now = datetime.utcnow()

    # Si no hay cache o expiró, hacer check real
    if (_last_db_check["timestamp"] is None or 
        (now - _last_db_check["timestamp"]).total_seconds() > _last_db_check["cache_duration"]):

        try:
            from app.db.init_db import check_database_connection
            db_status = check_database_connection()

            response_time = (time.time() - start_time) * 1000  # Convertir a ms
            system_metrics = get_system_metrics()

            _last_db_check.update({
                "timestamp": now,
                "status": db_status,
                "response_time_ms": response_time,
                "cpu_usage": system_metrics["cpu_percent"],
                "memory_usage": system_metrics["memory_percent"],
                "system_metrics": system_metrics
            })

            logger.info(f"DB Check realizado: {db_status}, Response time: {response_time:.2f}ms")
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Error en DB check: {e}, Response time: {response_time:.2f}ms")
            _last_db_check.update({
                "timestamp": now,
                "status": False,
                "response_time_ms": response_time,
                "cpu_usage": 0,
                "memory_usage": 0
            })

    return _last_db_check


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


@router.get("/health/detailed", status_code=status.HTTP_200_OK)
async def detailed_health_check(response: Response):
    """
    Health check detallado con análisis de impacto en performance

    - Verifica DB con métricas de respuesta
    - Incluye métricas del sistema
    - Análisis de impacto en recursos
    - Alertas de umbrales críticos
    """
    start_time = time.time()
    settings = get_settings()

    try:
        # Obtener métricas del sistema
        system_metrics = get_system_metrics()

        # Verificar DB con cache
        db_check = check_database_cached()

        # Calcular tiempo total de respuesta
        total_response_time = (time.time() - start_time) * 1000

        # Análisis de impacto
        impact_analysis = {
            "health_check_overhead": {
                "response_time_ms": total_response_time,
                "cpu_usage_percent": system_metrics["cpu_percent"],
                "memory_usage_percent": system_metrics["memory_percent"],
                "impact_level": "LOW" if total_response_time < MAX_RESPONSE_TIME_MS else "MEDIUM"
            },
            "system_status": {
                "cpu_healthy": system_metrics["cpu_percent"] < CPU_THRESHOLD_PERCENT,
                "memory_healthy": system_metrics["memory_percent"] < MEMORY_THRESHOLD_PERCENT,
                "disk_healthy": system_metrics["disk_percent"] < DISK_THRESHOLD_PERCENT
            },
            "alerts": []
        }

        # Generar alertas si hay umbrales excedidos
        if system_metrics["cpu_percent"] > CPU_THRESHOLD_PERCENT:
            impact_analysis["alerts"].append({
                "type": "CPU_HIGH",
                "message": f"CPU usage {system_metrics['cpu_percent']:.1f}% exceeds threshold {CPU_THRESHOLD_PERCENT}%",
                "severity": "WARNING"
            })

        if system_metrics["memory_percent"] > MEMORY_THRESHOLD_PERCENT:
            impact_analysis["alerts"].append({
                "type": "MEMORY_HIGH",
                "message": f"Memory usage {system_metrics['memory_percent']:.1f}% exceeds threshold {MEMORY_THRESHOLD_PERCENT}%",
                "severity": "WARNING"
            })

        if system_metrics["disk_percent"] > DISK_THRESHOLD_PERCENT:
            impact_analysis["alerts"].append({
                "type": "DISK_HIGH",
                "message": f"Disk usage {system_metrics['disk_percent']:.1f}% exceeds threshold {DISK_THRESHOLD_PERCENT}%",
                "severity": "CRITICAL"
            })

        # Determinar estado general
        overall_status = "healthy"
        if not db_check["status"]:
            overall_status = "unhealthy"
        elif impact_analysis["alerts"]:
            overall_status = "degraded"

        return {
            "status": overall_status,
            "service": "pagos-backend",
            "timestamp": datetime.utcnow().isoformat(),
            "database": {
                "status": "connected" if db_check["status"] else "disconnected",
                "response_time_ms": db_check.get("response_time_ms", 0),
                "last_check": db_check.get("timestamp", datetime.utcnow()).isoformat()
            },
            "system_metrics": system_metrics,
            "impact_analysis": impact_analysis,
            "environment": settings.ENVIRONMENT,
            "version": settings.APP_VERSION
        }

    except Exception as e:
        logger.error(f"Error en health check detallado: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unhealthy",
            "service": "pagos-backend",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "response_time_ms": (time.time() - start_time) * 1000
        }

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

        tables_to_drop = TABLES_TO_DROP

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
