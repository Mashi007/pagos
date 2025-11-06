# backend/app/api/v1/endpoints/health.py
"""Health Checks con Análisis de Impacto en Performance

Implementa monitoreo de salud del sistema con análisis de impacto
"""

import logging
import time
from typing import Any, Dict

import psutil
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text

from app.api.deps import get_current_user, get_db
from app.core.cache import cache_backend
from app.core.config import settings
from app.core.performance_monitor import performance_monitor
from app.db.session import engine
from app.models.user import User
from sqlalchemy.orm import Session

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


@router.get("/cache/status")
async def cache_status():
    """
    Verificar estado y operatividad del sistema de cache

    Retorna:
    - Tipo de cache (Redis o MemoryCache)
    - Estado de conexión
    - Pruebas de lectura/escritura
    - Configuración de Redis (si aplica)
    """
    try:
        from app.core.cache import MemoryCache

        # Determinar tipo de cache
        cache_type = "MemoryCache" if isinstance(cache_backend, MemoryCache) else "RedisCache"

        # Información de configuración
        config_info = {
            "REDIS_URL": bool(settings.REDIS_URL),
            "REDIS_HOST": settings.REDIS_HOST,
            "REDIS_PORT": settings.REDIS_PORT,
            "REDIS_DB": settings.REDIS_DB,
            "REDIS_PASSWORD": bool(settings.REDIS_PASSWORD),
            "REDIS_SOCKET_TIMEOUT": settings.REDIS_SOCKET_TIMEOUT,
        }

        # Pruebas de operatividad
        test_results = {
            "write_test": False,
            "read_test": False,
            "delete_test": False,
            "errors": [],
        }

        test_key = "health_check_test_key"
        test_value = {"test": True, "timestamp": time.time()}

        # Prueba de escritura
        try:
            write_success = cache_backend.set(test_key, test_value, ttl=10)
            test_results["write_test"] = write_success
            if not write_success:
                test_results["errors"].append("Error al escribir en cache")
        except Exception as e:
            test_results["errors"].append(f"Error en prueba de escritura: {str(e)}")
            logger.error(f"Error en prueba de escritura de cache: {e}")

        # Prueba de lectura
        try:
            read_value = cache_backend.get(test_key)
            test_results["read_test"] = read_value is not None and read_value.get("test") is True
            if not test_results["read_test"]:
                test_results["errors"].append("Error al leer del cache o valor incorrecto")
        except Exception as e:
            test_results["errors"].append(f"Error en prueba de lectura: {str(e)}")
            logger.error(f"Error en prueba de lectura de cache: {e}")

        # Prueba de eliminación
        try:
            delete_success = cache_backend.delete(test_key)
            test_results["delete_test"] = delete_success
            if not delete_success:
                test_results["errors"].append("Error al eliminar del cache")
        except Exception as e:
            test_results["errors"].append(f"Error en prueba de eliminación: {str(e)}")
            logger.error(f"Error en prueba de eliminación de cache: {e}")

        # Verificar si Redis está realmente conectado (solo para RedisCache)
        redis_connected = False
        if cache_type == "RedisCache":
            try:
                # Intentar hacer un ping a Redis
                if hasattr(cache_backend, "client"):
                    cache_backend.client.ping()
                    redis_connected = True
            except Exception as e:
                test_results["errors"].append(f"Redis no responde al ping: {str(e)}")
                logger.error(f"Redis ping failed: {e}")

        # Determinar estado general
        all_tests_passed = test_results["write_test"] and test_results["read_test"] and test_results["delete_test"]
        if cache_type == "RedisCache":
            all_tests_passed = all_tests_passed and redis_connected

        status = "operational" if all_tests_passed else "degraded"
        if test_results["errors"]:
            status = "error"

        # Advertencias
        warnings = []
        if cache_type == "MemoryCache":
            warnings.append("⚠️ Usando MemoryCache - NO recomendado para producción con múltiples workers")
            warnings.append("⚠️ El cache no se comparte entre workers, puede causar inconsistencias")
        if not settings.REDIS_URL and cache_type == "MemoryCache":
            warnings.append("⚠️ REDIS_URL no configurada - usando fallback MemoryCache")

        return {
            "status": status,
            "cache_type": cache_type,
            "redis_connected": redis_connected if cache_type == "RedisCache" else None,
            "config": config_info,
            "tests": test_results,
            "warnings": warnings,
            "timestamp": time.time(),
        }

    except Exception as e:
        logger.error(f"Error verificando estado de cache: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e),
            "timestamp": time.time(),
        }


@router.get("/database/indexes")
async def verify_database_indexes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Verificar que los índices críticos de performance estén creados correctamente

    Valida los índices creados por las migraciones:
    - 20251104_add_critical_performance_indexes
    - 20251104_add_group_by_indexes
    """
    from sqlalchemy import inspect

    try:
        inspector = inspect(db.bind)
        results = {
            "status": "success",
            "timestamp": time.time(),
            "indexes": {},
            "missing_indexes": [],
            "summary": {
                "total_expected": 0,
                "total_found": 0,
                "total_missing": 0,
            },
        }

        # Lista de índices esperados según las migraciones
        expected_indexes = {
            "notificaciones": [
                "idx_notificaciones_estado",
                "idx_notificaciones_tipo",
                "idx_notificaciones_fecha_creacion",
            ],
            "pagos_staging": [
                "idx_pagos_staging_fecha_pago",
                "idx_pagos_staging_monto_pagado",
                "idx_pagos_staging_extract_year",
                "idx_pagos_staging_extract_year_month",
            ],
            "cuotas": [
                "idx_cuotas_vencimiento_estado",
                "idx_cuotas_prestamo_id",
                "idx_cuotas_extract_year_month",
            ],
            "prestamos": [
                "idx_prestamos_estado",
                "idx_prestamos_cedula",
            ],
            "pagos": [
                "ix_pagos_fecha_registro",
            ],
        }

        # Verificar cada tabla e índice
        for table_name, index_names in expected_indexes.items():
            results["indexes"][table_name] = {}
            results["summary"]["total_expected"] += len(index_names)

            # Verificar si la tabla existe
            try:
                table_exists = table_name in inspector.get_table_names()
            except Exception:
                table_exists = False

            if not table_exists:
                results["indexes"][table_name] = {"table_exists": False, "indexes": {}}
                results["summary"]["total_missing"] += len(index_names)
                for idx_name in index_names:
                    results["missing_indexes"].append(f"{table_name}.{idx_name}")
                continue

            results["indexes"][table_name] = {"table_exists": True, "indexes": {}}

            # Obtener índices existentes en la tabla
            try:
                existing_indexes = inspector.get_indexes(table_name)
                existing_index_names = [idx["name"] for idx in existing_indexes]
            except Exception as e:
                existing_index_names = []
                results["indexes"][table_name]["error"] = str(e)

            # Verificar cada índice esperado
            for idx_name in index_names:
                exists = idx_name in existing_index_names
                results["indexes"][table_name]["indexes"][idx_name] = {"exists": exists, "status": "✅" if exists else "❌"}

                if exists:
                    results["summary"]["total_found"] += 1
                else:
                    results["summary"]["total_missing"] += 1
                    results["missing_indexes"].append(f"{table_name}.{idx_name}")

        # Determinar estado general
        if results["summary"]["total_missing"] == 0:
            results["status"] = "success"
            results["message"] = "✅ Todos los índices críticos están presentes"
        elif results["summary"]["total_missing"] < results["summary"]["total_expected"]:
            results["status"] = "partial"
            results["message"] = (
                f"⚠️ Faltan {results['summary']['total_missing']} de {results['summary']['total_expected']} índices"
            )
        else:
            results["status"] = "error"
            results["message"] = f"❌ No se encontraron índices críticos"

        # Obtener información adicional de índices funcionales usando SQL directo
        try:
            func_indexes_query = text(
                """
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    indexdef
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND (
                    indexname LIKE 'idx_%extract%'
                    OR indexname LIKE 'idx_%_extract%'
                  )
                ORDER BY tablename, indexname
            """
            )
            func_indexes_result = db.execute(func_indexes_query)
            func_indexes = []
            for row in func_indexes_result:
                func_indexes.append({"table": row.tablename, "name": row.indexname, "definition": row.indexdef})
            results["functional_indexes"] = func_indexes
        except Exception as e:
            results["functional_indexes"] = []
            results["functional_indexes_error"] = str(e)

        return results

    except Exception as e:
        logger.error(f"Error verificando índices: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e),
            "timestamp": time.time(),
        }
