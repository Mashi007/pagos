# backend/app/api/v1/endpoints/health.py
"""Health Checks con Análisis de Impacto en Performance

Implementa monitoreo de salud del sistema con análisis de impacto
"""

import logging
import time
from typing import Any, Dict

import psutil
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.cache import cache_backend
from app.core.config import settings
from app.core.performance_monitor import performance_monitor
from app.db.session import engine
from app.models.user import User

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
async def cors_debug(
    current_user: User = Depends(get_current_user),
):
    """Endpoint para debuggear CORS

    ⚠️ REQUIERE AUTENTICACIÓN
    ⚠️ Solo disponible en desarrollo
    """
    # Solo permitir en desarrollo
    if settings.ENVIRONMENT == "production":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint no disponible en producción",
        )
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
    """Readiness check para Kubernetes/Docker con timeout"""
    try:
        # Verificar conexión a DB con timeout usando check_database_cached
        # que ya tiene cache y manejo de errores
        db_check = check_database_cached()
        db_status = db_check.get("status", False)

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
async def performance_summary(
    current_user: User = Depends(get_current_user),
):
    """Obtener resumen general de performance de todos los endpoints

    ⚠️ REQUIERE AUTENTICACIÓN Y PERMISOS DE ADMINISTRADOR
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores pueden ver resumen de performance",
        )
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
async def performance_slow_endpoints(
    threshold_ms: float = 1000,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
):
    """
    Obtener endpoints lentos ordenados por tiempo promedio

    Args:
        threshold_ms: Umbral mínimo de tiempo en ms (default: 1000ms)
        limit: Número máximo de resultados (default: 20)

    ⚠️ REQUIERE AUTENTICACIÓN Y PERMISOS DE ADMINISTRADOR
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores pueden ver endpoints lentos",
        )
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
async def performance_endpoint_stats(
    method: str,
    path: str,
    current_user: User = Depends(get_current_user),
):
    """
    Obtener estadísticas detalladas de un endpoint específico

    Args:
        method: Método HTTP (GET, POST, etc.)
        path: Ruta del endpoint

    ⚠️ REQUIERE AUTENTICACIÓN Y PERMISOS DE ADMINISTRADOR
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores pueden ver estadísticas de endpoints",
        )
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
async def performance_recent_requests(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
):
    """
    Obtener peticiones recientes

    Args:
        limit: Número máximo de peticiones a retornar (default: 50, max: 200)

    ⚠️ REQUIERE AUTENTICACIÓN Y PERMISOS DE ADMINISTRADOR
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores pueden ver peticiones recientes",
        )
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
async def cache_status(
    current_user: User = Depends(get_current_user),
):
    """
    Verificar estado y operatividad del sistema de cache

    Retorna:
    - Tipo de cache (Redis o MemoryCache)
    - Estado de conexión
    - Pruebas de lectura/escritura
    - Configuración de Redis (si aplica)

    ⚠️ REQUIERE AUTENTICACIÓN Y PERMISOS DE ADMINISTRADOR
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores pueden ver estado del cache",
        )
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

        cache_status_value = "operational" if all_tests_passed else "degraded"
        if test_results["errors"]:
            cache_status_value = "error"

        # Advertencias
        warnings = []
        if cache_type == "MemoryCache":
            warnings.append("⚠️ Usando MemoryCache - NO recomendado para producción con múltiples workers")
            warnings.append("⚠️ El cache no se comparte entre workers, puede causar inconsistencias")
        if not settings.REDIS_URL and cache_type == "MemoryCache":
            warnings.append("⚠️ REDIS_URL no configurada - usando fallback MemoryCache")

        return {
            "status": cache_status_value,
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

    ⚠️ REQUIERE AUTENTICACIÓN Y PERMISOS DE ADMINISTRADOR
    """
    # Verificar que el usuario sea administrador
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores pueden verificar índices de la base de datos",
        )
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
            results["message"] = "❌ No se encontraron índices críticos"

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


@router.get("/database/tabla-documentos-ai")
async def verificar_tabla_documentos_ai(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Verifica si la tabla documentos_ai existe en la base de datos
    """
    try:
        from sqlalchemy import inspect, text

        inspector = inspect(db.bind)
        tablas = inspector.get_table_names()

        resultado = {
            "tabla_existe": False,
            "tabla_nombre": "documentos_ai",
            "total_tablas": len(tablas),
            "columnas": [],
            "indices": [],
            "total_documentos": 0,
            "mensaje": "",
        }

        if "documentos_ai" in tablas:
            resultado["tabla_existe"] = True
            resultado["mensaje"] = "✅ La tabla 'documentos_ai' existe"

            # Obtener información de columnas
            columnas = inspector.get_columns("documentos_ai")
            resultado["columnas"] = [
                {
                    "nombre": col["name"],
                    "tipo": str(col["type"]),
                    "nullable": col["nullable"],
                    "default": str(col.get("default", "")) if col.get("default") else None,
                }
                for col in columnas
            ]

            # Obtener índices
            indices = inspector.get_indexes("documentos_ai")
            resultado["indices"] = [
                {
                    "nombre": idx["name"],
                    "columnas": idx["column_names"],
                    "unique": idx.get("unique", False),
                }
                for idx in indices
            ]

            # Contar documentos
            try:
                count_result = db.execute(text("SELECT COUNT(*) FROM documentos_ai"))
                resultado["total_documentos"] = count_result.scalar() or 0
            except Exception as e:
                resultado["mensaje"] += f" (Error contando documentos: {str(e)})"
        else:
            resultado["mensaje"] = "❌ La tabla 'documentos_ai' NO existe. Ejecuta las migraciones: alembic upgrade head"
            resultado["tablas_disponibles"] = sorted(tablas)[:20]  # Primeras 20 tablas

        return resultado

    except Exception as e:
        logger.error(f"Error verificando tabla documentos_ai: {e}", exc_info=True)
        return {
            "tabla_existe": False,
            "error": str(e),
            "mensaje": f"❌ Error verificando tabla: {str(e)}",
        }


@router.post("/database/indexes/create")
async def create_database_indexes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Crear índices críticos de performance manualmente

    Útil si las migraciones de Alembic no se ejecutaron correctamente.
    Ejecuta la creación de índices usando SQL directo.

    ⚠️ REQUIERE AUTENTICACIÓN Y PERMISOS DE ADMINISTRADOR
    """
    # Verificar que el usuario sea administrador
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores pueden crear índices en la base de datos",
        )
    from sqlalchemy import inspect

    try:
        inspector = inspect(db.bind)
        results = {
            "status": "success",
            "timestamp": time.time(),
            "created": [],
            "skipped": [],
            "errors": [],
        }

        def _index_exists(table_name: str, index_name: str) -> bool:
            try:
                indexes = inspector.get_indexes(table_name)
                return any(idx["name"] == index_name for idx in indexes)
            except Exception:
                return False

        def _table_exists(table_name: str) -> bool:
            try:
                return table_name in inspector.get_table_names()
            except Exception:
                return False

        def _column_exists(table_name: str, column_name: str) -> bool:
            try:
                columns = inspector.get_columns(table_name)
                return any(col["name"] == column_name for col in columns)
            except Exception:
                return False

        # Crear índices críticos manualmente usando SQL directo
        indices_to_create = [
            # Notificaciones
            ("notificaciones", "idx_notificaciones_estado", "estado", None),
            ("notificaciones", "idx_notificaciones_tipo", "tipo", None),
            ("notificaciones", "idx_notificaciones_fecha_creacion", "fecha_creacion", None),
            # Cuotas
            ("cuotas", "idx_cuotas_vencimiento_estado", "fecha_vencimiento, estado", "WHERE estado != 'PAGADO'"),
            ("cuotas", "idx_cuotas_prestamo_id", "prestamo_id", None),
            (
                "cuotas",
                "idx_cuotas_extract_year_month",
                "EXTRACT(YEAR FROM fecha_vencimiento), EXTRACT(MONTH FROM fecha_vencimiento)",
                "WHERE fecha_vencimiento IS NOT NULL",
            ),
            # Prestamos
            ("prestamos", "idx_prestamos_estado", "estado", None),
            ("prestamos", "idx_prestamos_cedula", "cedula", None),
            # Pagos
            ("pagos", "ix_pagos_fecha_registro", "fecha_registro", None),
        ]

        # Índices funcionales de pagos_staging (requieren SQL especial)
        pagos_staging_indices = [
            (
                "pagos_staging",
                "idx_pagos_staging_fecha_timestamp",
                "USING btree ((fecha_pago::timestamp))",
                "WHERE fecha_pago IS NOT NULL AND fecha_pago != ''",
            ),
            (
                "pagos_staging",
                "idx_pagos_staging_monto_numeric",
                "USING btree ((monto_pagado::numeric))",
                "WHERE monto_pagado IS NOT NULL AND monto_pagado != ''",
            ),
            (
                "pagos_staging",
                "idx_pagos_staging_extract_year",
                "USING btree (EXTRACT(YEAR FROM fecha_pago::timestamp))",
                "WHERE fecha_pago IS NOT NULL AND fecha_pago != '' AND fecha_pago ~ '^\\d{4}-\\d{2}-\\d{2}'",
            ),
            (
                "pagos_staging",
                "idx_pagos_staging_extract_year_month",
                "USING btree (EXTRACT(YEAR FROM fecha_pago::timestamp), EXTRACT(MONTH FROM fecha_pago::timestamp))",
                "WHERE fecha_pago IS NOT NULL AND fecha_pago != '' AND fecha_pago ~ '^\\d{4}-\\d{2}-\\d{2}'",
            ),
        ]

        # Crear índices normales
        for table_name, idx_name, columns, where_clause in indices_to_create:
            if not _table_exists(table_name):
                results["skipped"].append(f"{table_name}.{idx_name} (tabla no existe)")
                continue

            if _index_exists(table_name, idx_name):
                results["skipped"].append(f"{table_name}.{idx_name} (ya existe)")
                continue

            # Verificar que las columnas existen (para índices simples)
            if not columns.startswith("EXTRACT"):
                column_list = [c.strip() for c in columns.split(",")]
                if not all(_column_exists(table_name, col.strip()) for col in column_list):
                    results["skipped"].append(f"{table_name}.{idx_name} (columnas no existen)")
                    continue

            try:
                if where_clause:
                    sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name} ({columns}) {where_clause}"
                else:
                    sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name} ({columns})"

                db.execute(text(sql))
                db.commit()
                results["created"].append(f"{table_name}.{idx_name}")
                logger.info(f"✅ Índice '{idx_name}' creado en tabla '{table_name}'")
            except Exception as e:
                error_msg = str(e)
                results["errors"].append(f"{table_name}.{idx_name}: {error_msg}")
                logger.error(f"⚠️ Error creando índice '{idx_name}': {e}")
                try:
                    db.rollback()
                except Exception:
                    pass

        # Crear índices funcionales de pagos_staging
        for table_name, idx_name, index_definition, where_clause in pagos_staging_indices:
            if not _table_exists(table_name):
                results["skipped"].append(f"{table_name}.{idx_name} (tabla no existe)")
                continue

            if _index_exists(table_name, idx_name):
                results["skipped"].append(f"{table_name}.{idx_name} (ya existe)")
                continue

            try:
                if where_clause:
                    sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name} {index_definition} {where_clause}"
                else:
                    sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name} {index_definition}"

                db.execute(text(sql))
                db.commit()
                results["created"].append(f"{table_name}.{idx_name}")
                logger.info(f"✅ Índice funcional '{idx_name}' creado en tabla '{table_name}'")
            except Exception as e:
                error_msg = str(e)
                results["errors"].append(f"{table_name}.{idx_name}: {error_msg}")
                logger.error(f"⚠️ Error creando índice funcional '{idx_name}': {e}")
                try:
                    db.rollback()
                except Exception:
                    pass

        # Ejecutar ANALYZE para actualizar estadísticas
        try:
            tables_to_analyze = ["notificaciones", "cuotas", "prestamos", "pagos", "pagos_staging"]
            for table in tables_to_analyze:
                if _table_exists(table):
                    try:
                        db.execute(text(f"ANALYZE {table}"))
                        db.commit()
                        logger.info(f"✅ ANALYZE ejecutado en '{table}'")
                    except Exception as e:
                        logger.warning(f"⚠️ No se pudo ejecutar ANALYZE en '{table}': {e}")
        except Exception as e:
            logger.warning(f"⚠️ Advertencia al ejecutar ANALYZE: {e}")

        # Determinar estado
        if results["errors"]:
            results["status"] = "partial" if results["created"] else "error"
        elif not results["created"]:
            results["status"] = "info"
            results["message"] = "Todos los índices ya existen o no se pudieron crear"
        else:
            results["status"] = "success"
            results["message"] = f"✅ {len(results['created'])} índices creados exitosamente"

        return results

    except Exception as e:
        logger.error(f"Error creando índices: {e}", exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass
        return {
            "status": "error",
            "message": str(e),
            "timestamp": time.time(),
        }


@router.get("/database/indexes/performance")
async def monitor_indexes_performance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Monitorear el rendimiento de los endpoints del dashboard después de crear índices

    Ejecuta queries de prueba para medir tiempos de respuesta y comparar
    con los tiempos esperados después de crear los índices.

    ⚠️ REQUIERE AUTENTICACIÓN Y PERMISOS DE ADMINISTRADOR
    """
    # Verificar que el usuario sea administrador
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores pueden monitorear performance de índices",
        )
    try:
        results = {
            "status": "success",
            "timestamp": time.time(),
            "endpoints": {},
            "summary": {
                "total_tested": 0,
                "fast_endpoints": 0,
                "slow_endpoints": 0,
                "improvement_detected": False,
            },
        }

        # Endpoints críticos del dashboard a monitorear
        dashboard_endpoints = {
            "financiamiento_tendencia_mensual": {
                "query": """
                    SELECT
                        EXTRACT(YEAR FROM fecha_aprobacion) as año,
                        EXTRACT(MONTH FROM fecha_aprobacion) as mes,
                        COUNT(*) as total,
                        SUM(monto_financiado) as monto_total
                    FROM prestamos
                    WHERE estado = 'APROBADO'
                      AND fecha_aprobacion >= CURRENT_DATE - INTERVAL '12 months'
                    GROUP BY EXTRACT(YEAR FROM fecha_aprobacion), EXTRACT(MONTH FROM fecha_aprobacion)
                    ORDER BY año, mes
                """,
                "expected_max_ms": 2000,  # 2 segundos máximo
                "description": "Tendencia mensual de financiamientos",
            },
            "evolucion_pagos": {
                "query": """
                    SELECT
                        EXTRACT(YEAR FROM fecha_pago) as año,
                        EXTRACT(MONTH FROM fecha_pago) as mes,
                        SUM(monto_pagado) as total_pagado
                    FROM pagos
                    WHERE activo = TRUE
                      AND fecha_pago >= CURRENT_DATE - INTERVAL '6 months'
                    GROUP BY EXTRACT(YEAR FROM fecha_pago), EXTRACT(MONTH FROM fecha_pago)
                    ORDER BY año, mes
                """,
                "expected_max_ms": 1500,  # 1.5 segundos máximo
                "description": "Evolución de pagos mensuales",
            },
            "cobranzas_mensuales": {
                "query": """
                    SELECT
                        EXTRACT(YEAR FROM fecha_vencimiento) as año,
                        EXTRACT(MONTH FROM fecha_vencimiento) as mes,
                        COUNT(*) as total_cuotas,
                        SUM(CASE WHEN estado != 'PAGADO' THEN 1 ELSE 0 END) as cuotas_pendientes
                    FROM cuotas
                    WHERE fecha_vencimiento >= CURRENT_DATE - INTERVAL '6 months'
                    GROUP BY EXTRACT(YEAR FROM fecha_vencimiento), EXTRACT(MONTH FROM fecha_vencimiento)
                    ORDER BY año, mes
                """,
                "expected_max_ms": 1500,  # 1.5 segundos máximo
                "description": "Cobranzas mensuales",
            },
            "notificaciones_estadisticas": {
                "query": """
                    SELECT
                        estado,
                        COUNT(*) as total
                    FROM notificaciones
                    GROUP BY estado
                """,
                "expected_max_ms": 500,  # 500ms máximo
                "description": "Estadísticas de notificaciones",
            },
        }

        # Ejecutar queries de prueba y medir tiempos
        for endpoint_name, endpoint_config in dashboard_endpoints.items():
            start_time = time.time()
            try:
                result = db.execute(text(endpoint_config["query"]))
                rows = result.fetchall()
                elapsed_ms = (time.time() - start_time) * 1000

                is_fast = elapsed_ms <= endpoint_config["expected_max_ms"]

                results["endpoints"][endpoint_name] = {
                    "description": endpoint_config["description"],
                    "response_time_ms": round(elapsed_ms, 2),
                    "expected_max_ms": endpoint_config["expected_max_ms"],
                    "status": "fast" if is_fast else "slow",
                    "rows_returned": len(rows),
                    "improvement": "✅ Mejora detectada" if is_fast else "⚠️ Aún lento",
                }

                results["summary"]["total_tested"] += 1
                if is_fast:
                    results["summary"]["fast_endpoints"] += 1
                else:
                    results["summary"]["slow_endpoints"] += 1

            except Exception as e:
                elapsed_ms = (time.time() - start_time) * 1000
                results["endpoints"][endpoint_name] = {
                    "description": endpoint_config["description"],
                    "response_time_ms": round(elapsed_ms, 2),
                    "expected_max_ms": endpoint_config["expected_max_ms"],
                    "status": "error",
                    "error": str(e),
                }
                results["summary"]["total_tested"] += 1
                logger.error(f"Error en query de prueba para {endpoint_name}: {e}")

        # Determinar si hay mejoras
        if results["summary"]["fast_endpoints"] > 0:
            results["summary"]["improvement_detected"] = True

        # Mensaje de resumen
        if results["summary"]["slow_endpoints"] == 0:
            results["message"] = "✅ Todos los endpoints están dentro de los tiempos esperados"
        elif results["summary"]["fast_endpoints"] > 0:
            results["message"] = f"⚠️ {results['summary']['slow_endpoints']} endpoints aún están lentos, pero hay mejoras"
        else:
            results["message"] = "❌ Los endpoints aún están lentos, verificar índices"

        return results

    except Exception as e:
        logger.error(f"Error monitoreando rendimiento de índices: {e}", exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass
        return {
            "status": "error",
            "message": str(e),
            "timestamp": time.time(),
        }


@router.get("/processes/pending")
async def check_pending_processes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Verifica procesos pendientes o incompletos en el sistema

    Revisa:
    - Fine-tuning jobs pendientes o en ejecución
    - Notificaciones pendientes
    - Pagos no conciliados
    - Cuotas con estados inconsistentes
    - Préstamos pendientes
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores pueden ver procesos pendientes",
        )

    try:
        from datetime import date, datetime, timedelta

        from sqlalchemy import and_, func, or_

        from app.models.amortizacion import Cuota
        from app.models.notificacion import Notificacion
        from app.models.pago import Pago
        from app.models.prestamo import Prestamo

        resultado = {
            "timestamp": time.time(),
            "fecha_revision": datetime.now().isoformat(),
            "procesos_pendientes": {},
            "resumen": {
                "total_procesos_pendientes": 0,
                "prioridad_alta": 0,
                "prioridad_media": 0,
                "prioridad_baja": 0,
            },
        }

        # 1. Fine-tuning jobs pendientes o en ejecución
        try:
            from app.models.fine_tuning_job import FineTuningJob

            jobs_pendientes = db.query(FineTuningJob).filter(FineTuningJob.status.in_(["pending", "running"])).all()

            jobs_antiguos = (
                db.query(FineTuningJob)
                .filter(
                    FineTuningJob.status.in_(["pending", "running"]),
                    FineTuningJob.creado_en < datetime.now() - timedelta(days=7),
                )
                .count()
            )

            resultado["procesos_pendientes"]["fine_tuning_jobs"] = {
                "total_pendientes": len(jobs_pendientes),
                "jobs_antiguos_7_dias": jobs_antiguos,
                "detalles": [
                    {
                        "id": job.id,
                        "openai_job_id": job.openai_job_id,
                        "status": job.status,
                        "creado_en": job.creado_en.isoformat() if job.creado_en else None,
                        "progreso": job.progreso,
                        "error": job.error,
                    }
                    for job in jobs_pendientes[:10]  # Limitar a 10 para no sobrecargar
                ],
                "prioridad": "media" if len(jobs_pendientes) > 0 else "baja",
            }

            if len(jobs_pendientes) > 0:
                resultado["resumen"]["total_procesos_pendientes"] += len(jobs_pendientes)
                resultado["resumen"]["prioridad_media"] += len(jobs_pendientes)
        except Exception as e:
            logger.warning(f"Error verificando fine-tuning jobs: {e}")
            resultado["procesos_pendientes"]["fine_tuning_jobs"] = {
                "error": str(e),
                "total_pendientes": 0,
            }

        # 2. Notificaciones pendientes
        try:
            notificaciones_pendientes = db.query(Notificacion).filter(Notificacion.estado == "PENDIENTE").count()

            notificaciones_antiguas = (
                db.query(Notificacion)
                .filter(
                    Notificacion.estado == "PENDIENTE",
                    Notificacion.fecha_creacion < datetime.now() - timedelta(days=3),
                )
                .count()
            )

            resultado["procesos_pendientes"]["notificaciones"] = {
                "total_pendientes": notificaciones_pendientes,
                "antiguas_3_dias": notificaciones_antiguas,
                "prioridad": "alta" if notificaciones_antiguas > 0 else "media" if notificaciones_pendientes > 0 else "baja",
            }

            if notificaciones_pendientes > 0:
                resultado["resumen"]["total_procesos_pendientes"] += notificaciones_pendientes
                if notificaciones_antiguas > 0:
                    resultado["resumen"]["prioridad_alta"] += notificaciones_antiguas
                else:
                    resultado["resumen"]["prioridad_media"] += notificaciones_pendientes
        except Exception as e:
            logger.warning(f"Error verificando notificaciones: {e}")
            resultado["procesos_pendientes"]["notificaciones"] = {
                "error": str(e),
                "total_pendientes": 0,
            }

        # 3. Pagos no conciliados
        try:
            pagos_no_conciliados = (
                db.query(Pago)
                .filter(
                    Pago.conciliado.is_(False),
                    Pago.activo.is_(True),
                )
                .count()
            )

            pagos_antiguos_no_conciliados = (
                db.query(Pago)
                .filter(
                    Pago.conciliado.is_(False),
                    Pago.activo.is_(True),
                    Pago.fecha_registro < datetime.now() - timedelta(days=7),
                )
                .count()
            )

            resultado["procesos_pendientes"]["pagos_no_conciliados"] = {
                "total_no_conciliados": pagos_no_conciliados,
                "antiguos_7_dias": pagos_antiguos_no_conciliados,
                "prioridad": "alta" if pagos_antiguos_no_conciliados > 0 else "media" if pagos_no_conciliados > 0 else "baja",
            }

            if pagos_no_conciliados > 0:
                resultado["resumen"]["total_procesos_pendientes"] += pagos_no_conciliados
                if pagos_antiguos_no_conciliados > 0:
                    resultado["resumen"]["prioridad_alta"] += pagos_antiguos_no_conciliados
                else:
                    resultado["resumen"]["prioridad_media"] += pagos_no_conciliados
        except Exception as e:
            logger.warning(f"Error verificando pagos no conciliados: {e}")
            resultado["procesos_pendientes"]["pagos_no_conciliados"] = {
                "error": str(e),
                "total_no_conciliados": 0,
            }

        # 4. Cuotas con estados inconsistentes (total_pagado >= monto_cuota pero estado != PAGADO)
        try:
            # hoy calculado pero no usado en esta función
            # hoy = date.today()
            cuotas_inconsistentes = (
                db.query(Cuota)
                .filter(
                    Cuota.total_pagado >= Cuota.monto_cuota,
                    Cuota.estado != "PAGADO",
                )
                .count()
            )

            resultado["procesos_pendientes"]["cuotas_inconsistentes"] = {
                "total_inconsistentes": cuotas_inconsistentes,
                "descripcion": "Cuotas con total_pagado >= monto_cuota pero estado != PAGADO",
                "prioridad": "alta" if cuotas_inconsistentes > 0 else "baja",
            }

            if cuotas_inconsistentes > 0:
                resultado["resumen"]["total_procesos_pendientes"] += cuotas_inconsistentes
                resultado["resumen"]["prioridad_alta"] += cuotas_inconsistentes
        except Exception as e:
            logger.warning(f"Error verificando cuotas inconsistentes: {e}")
            resultado["procesos_pendientes"]["cuotas_inconsistentes"] = {
                "error": str(e),
                "total_inconsistentes": 0,
            }

        # 5. Préstamos pendientes (si aplica)
        try:
            prestamos_pendientes = db.query(Prestamo).filter(Prestamo.estado == "PENDIENTE").count()

            resultado["procesos_pendientes"]["prestamos_pendientes"] = {
                "total_pendientes": prestamos_pendientes,
                "prioridad": "media" if prestamos_pendientes > 0 else "baja",
            }

            if prestamos_pendientes > 0:
                resultado["resumen"]["total_procesos_pendientes"] += prestamos_pendientes
                resultado["resumen"]["prioridad_media"] += prestamos_pendientes
        except Exception as e:
            logger.warning(f"Error verificando préstamos pendientes: {e}")
            resultado["procesos_pendientes"]["prestamos_pendientes"] = {
                "error": str(e),
                "total_pendientes": 0,
            }

        # Determinar estado general
        if resultado["resumen"]["prioridad_alta"] > 0:
            resultado["estado_general"] = "critico"
        elif resultado["resumen"]["prioridad_media"] > 0:
            resultado["estado_general"] = "advertencia"
        elif resultado["resumen"]["total_procesos_pendientes"] > 0:
            resultado["estado_general"] = "info"
        else:
            resultado["estado_general"] = "ok"

        return resultado

    except Exception as e:
        logger.error(f"Error verificando procesos pendientes: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e),
            "timestamp": time.time(),
        }


@router.get("/files/duplicates")
async def check_duplicate_files(
    current_user: User = Depends(get_current_user),
):
    """
    Verifica archivos duplicados o que puedan generar interferencia

    Revisa:
    - Archivos con nombres similares
    - Funciones/clases duplicadas
    - Imports conflictivos
    - Archivos no registrados
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores pueden verificar archivos duplicados",
        )

    try:
        import os
        from collections import defaultdict
        from pathlib import Path

        resultado = {
            "timestamp": time.time(),
            "archivos_duplicados": {},
            "archivos_similares": {},
            "posibles_conflictos": {},
            "archivos_no_registrados": [],
            "resumen": {
                "total_duplicados": 0,
                "total_similares": 0,
                "total_conflictos": 0,
                "total_no_registrados": 0,
            },
        }

        # Obtener ruta del backend
        backend_path = Path(__file__).parent.parent.parent.parent / "backend"
        app_path = backend_path / "app"

        # 1. Buscar archivos con nombres similares o duplicados
        archivos_por_nombre = defaultdict(list)

        for root, dirs, files in os.walk(app_path):
            # Ignorar __pycache__ y .pyc
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for file in files:
                if file.endswith(".py"):
                    nombre_base = file.replace(".py", "")
                    ruta_completa = Path(root) / file
                    ruta_relativa = ruta_completa.relative_to(backend_path)
                    archivos_por_nombre[nombre_base].append(str(ruta_relativa))

        # Identificar duplicados exactos y similares
        for nombre, rutas in archivos_por_nombre.items():
            if len(rutas) > 1:
                # Verificar si son realmente duplicados o solo nombres similares
                rutas_unicas = list(set(rutas))
                if len(rutas_unicas) > 1:
                    resultado["archivos_similares"][nombre] = {
                        "cantidad": len(rutas_unicas),
                        "ubicaciones": rutas_unicas,
                        "tipo": "similar" if len(rutas_unicas) == 2 else "multiple",
                    }
                    resultado["resumen"]["total_similares"] += len(rutas_unicas)

        # 2. Verificar servicios ML (posible duplicación)
        servicios_ml = []
        if (app_path / "services" / "ml_service.py").exists():
            servicios_ml.append("services/ml_service.py")
        if (app_path / "services" / "ml_impago_cuotas_service.py").exists():
            servicios_ml.append("services/ml_impago_cuotas_service.py")

        if len(servicios_ml) > 1:
            resultado["posibles_conflictos"]["servicios_ml"] = {
                "descripcion": "Múltiples servicios ML encontrados",
                "archivos": servicios_ml,
                "recomendacion": "Verificar que no haya funciones duplicadas o conflictos de nombres",
                "severidad": "media",
            }
            resultado["resumen"]["total_conflictos"] += 1

        # 3. Verificar archivos de notificaciones (muchos archivos similares)
        archivos_notificaciones = [
            str(p.relative_to(backend_path)) for p in app_path.rglob("*notificacion*.py") if p.is_file()
        ]

        if len(archivos_notificaciones) > 10:
            resultado["posibles_conflictos"]["notificaciones"] = {
                "descripcion": f"Muchos archivos de notificaciones ({len(archivos_notificaciones)})",
                "archivos": archivos_notificaciones[:15],  # Limitar a 15
                "total": len(archivos_notificaciones),
                "recomendacion": "Verificar si hay funcionalidad duplicada o si se pueden consolidar",
                "severidad": "baja",
            }
            resultado["resumen"]["total_conflictos"] += 1

        # 4. Verificar endpoints no registrados en __init__.py
        try:
            endpoints_path = app_path / "api" / "v1" / "endpoints"
            endpoints_registrados = set()

            # Leer __init__.py para ver qué está registrado
            init_file = endpoints_path / "__init__.py"
            if init_file.exists():
                with open(init_file, "r", encoding="utf-8") as f:
                    contenido = f.read()
                    # Buscar imports en el archivo
                    import re

                    imports = re.findall(r"from \. import (\w+)", contenido)
                    imports += re.findall(r"import (\w+)", contenido)
                    endpoints_registrados = set(imports)

            # Buscar archivos .py en endpoints
            archivos_endpoints = [
                f.stem for f in endpoints_path.glob("*.py") if f.name != "__init__.py" and f.name != "__pycache__"
            ]

            endpoints_no_registrados = [archivo for archivo in archivos_endpoints if archivo not in endpoints_registrados]

            if endpoints_no_registrados:
                resultado["archivos_no_registrados"] = endpoints_no_registrados
                resultado["resumen"]["total_no_registrados"] = len(endpoints_no_registrados)
        except Exception as e:
            logger.warning(f"Error verificando endpoints no registrados: {e}")
            resultado["archivos_no_registrados"] = []

        # 5. Verificar posibles conflictos de imports
        # posibles_conflictos_imports = []  # Variable no usada

        # Verificar si hay imports circulares potenciales
        archivos_imports_ml = []
        for archivo in app_path.rglob("*.py"):
            try:
                with open(archivo, "r", encoding="utf-8") as f:
                    contenido = f.read()
                    if "ml_service" in contenido or "ml_impago" in contenido:
                        archivos_imports_ml.append(str(archivo.relative_to(backend_path)))
            except Exception:
                pass

        if len(archivos_imports_ml) > 5:
            resultado["posibles_conflictos"]["imports_ml"] = {
                "descripcion": "Muchos archivos importan servicios ML",
                "archivos": archivos_imports_ml[:10],  # Limitar a 10
                "total": len(archivos_imports_ml),
                "recomendacion": "Verificar que no haya imports circulares",
                "severidad": "baja",
            }
            resultado["resumen"]["total_conflictos"] += 1

        # Determinar estado general
        if resultado["resumen"]["total_conflictos"] > 0 or resultado["resumen"]["total_no_registrados"] > 0:
            resultado["estado_general"] = "advertencia"
        elif resultado["resumen"]["total_similares"] > 0:
            resultado["estado_general"] = "info"
        else:
            resultado["estado_general"] = "ok"

        return resultado

    except Exception as e:
        logger.error(f"Error verificando archivos duplicados: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e),
            "timestamp": time.time(),
        }
