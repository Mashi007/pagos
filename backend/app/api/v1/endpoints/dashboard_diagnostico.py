"""
Dashboard de Diagnóstico en Tiempo Real
Sistema de monitoreo y auditoría para problemas de autenticación
"""

import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

# Almacenamiento en memoria para auditoría
audit_logs = deque(maxlen=1000)  # Mantener últimos 1000 logs
error_patterns = defaultdict(int)
request_stats = defaultdict(int)


class AuditLogger:
    """Logger especializado para auditoría de autenticación"""

    @staticmethod
    def log_request(
        request: Request,
        response: Response,
        user_id: str = None,
        error: str = None,
    ):
        """Registrar request en auditoría"""
        timestamp = datetime.now()

        log_entry = {
            "timestamp": timestamp.isoformat(),
            "method": request.method,
            "url": str(request.url),
            "status_code": response.status_code,
            "user_id": user_id,
            "user_agent": request.headers.get("user-agent", "unknown"),
            "ip": request.client.host if request.client else "unknown",
            "error": error,
            "auth_header_present": "authorization" in request.headers,
            "auth_header_type": (
                request.headers.get("authorization", "").split(" ")[0]
                if request.headers.get("authorization")
                else None
            ),
        }

        # Agregar al log
        audit_logs.append(log_entry)

        # Actualizar estadísticas
        request_stats[f"status_{response.status_code}"] += 1
        if error:
            error_patterns[error] += 1

        # Log específico para errores 401
        if response.status_code == 401:
            logger.warning(
                f"🔒 401 Unauthorized - {request.method} {request.url} - Error: {error}"
            )

    @staticmethod
    def get_recent_logs(minutes: int = 60) -> List[Dict]:
        """Obtener logs recientes"""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        return [
            log
            for log in audit_logs
            if datetime.fromisoformat(log["timestamp"]) > cutoff
        ]

    @staticmethod
    def get_error_summary() -> Dict[str, Any]:
        """Resumen de errores"""
        recent_logs = AuditLogger.get_recent_logs(60)

        # Agrupar por tipo de error
        error_counts = defaultdict(int)
        status_counts = defaultdict(int)

        for log in recent_logs:
            if log["error"]:
                error_counts[log["error"]] += 1
            status_counts[log["status_code"]] += 1

        return {
            "total_requests": len(recent_logs),
            "error_counts": dict(error_counts),
            "status_counts": dict(status_counts),
            "time_range": "last_60_minutes",
        }


@router.get("/dashboard")
async def dashboard_diagnostico(db: Session = Depends(get_db)):
    """
    📊 Dashboard principal de diagnóstico
    """
    try:
        # 1. Estadísticas generales del sistema
        system_stats = {
            "timestamp": datetime.now().isoformat(),
            "environment": settings.ENVIRONMENT,
            "debug_mode": settings.DEBUG,
            "cors_origins_count": len(settings.CORS_ORIGINS),
        }

        # 2. Estadísticas de usuarios
        try:
            total_users = db.query(User).count()
            active_users = db.query(User).filter(User.is_active).count()
            admin_users = db.query(User).filter(User.is_admin).count()

            user_stats = {
                "total_users": total_users,
                "active_users": active_users,
                "admin_users": admin_users,
                "inactive_users": total_users - active_users,
            }
        except Exception as e:
            user_stats = {"error": str(e)}

        # 3. Estadísticas de requests
        request_stats_summary = AuditLogger.get_error_summary()

        # 4. Logs recientes (últimos 20)
        recent_logs = AuditLogger.get_recent_logs(60)[-20:]

        # 5. Patrones de error más comunes
        top_errors = sorted(
            error_patterns.items(), key=lambda x: x[1], reverse=True
        )[:5]

        # 6. Análisis de autenticación
        auth_analysis = {
            "total_401_errors": request_stats_summary["status_counts"].get(
                401, 0
            ),
            "total_requests": request_stats_summary["total_requests"],
            "error_rate": (
                (
                    request_stats_summary["status_counts"].get(401, 0)
                    / max(request_stats_summary["total_requests"], 1)
                )
                * 100
            ),
        }

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "dashboard": {
                "system": system_stats,
                "users": user_stats,
                "requests": request_stats_summary,
                "auth_analysis": auth_analysis,
                "top_errors": top_errors,
                "recent_logs": recent_logs,
            },
            "recommendations": _generate_dashboard_recommendations(
                auth_analysis, user_stats
            ),
        }

    except Exception as e:
        logger.error(f"Error en dashboard de diagnóstico: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }


@router.get("/logs")
async def obtener_logs_auditoria(minutes: int = 60, limit: int = 100):
    """
    📝 Obtener logs de auditoría
    """
    try:
        logs = AuditLogger.get_recent_logs(minutes)

        # Limitar resultados
        if limit:
            logs = logs[-limit:]

        # Filtrar solo errores si se solicita
        error_logs = [log for log in logs if log["status_code"] >= 400]

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "logs": {
                "total_logs": len(logs),
                "error_logs": len(error_logs),
                "time_range_minutes": minutes,
                "logs": logs,
                "error_summary": AuditLogger.get_error_summary(),
            },
        }

    except Exception as e:
        logger.error(f"Error obteniendo logs de auditoría: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }


@router.get("/health-check")
async def health_check_detallado(db: Session = Depends(get_db)):
    """
    🏥 Health check detallado del sistema
    """
    try:
        checks = {}

        # 1. Verificar conexión a BD
        try:
            db.execute("SELECT 1")
            checks["database"] = {
                "status": "healthy",
                "message": "Database connection OK",
            }
        except Exception as e:
            checks["database"] = {
                "status": "unhealthy",
                "message": f"Database error: {str(e)}",
            }

        # 2. Verificar configuración JWT
        jwt_ok = bool(settings.SECRET_KEY and len(settings.SECRET_KEY) >= 32)
        checks["jwt_config"] = {
            "status": "healthy" if jwt_ok else "unhealthy",
            "message": (
                "JWT configuration OK"
                if jwt_ok
                else "JWT configuration issues"
            ),
            "secret_key_length": (
                len(settings.SECRET_KEY) if settings.SECRET_KEY else 0
            ),
        }

        # 3. Verificar usuarios admin
        try:
            admin_count = db.query(User).filter(User.is_admin).count()
            admin_ok = admin_count > 0
            checks["admin_users"] = {
                "status": "healthy" if admin_ok else "unhealthy",
                "message": (
                    f"Found {admin_count} admin users"
                    if admin_ok
                    else "No admin users found"
                ),
                "count": admin_count,
            }
        except Exception as e:
            checks["admin_users"] = {
                "status": "unhealthy",
                "message": f"Error checking admin users: {str(e)}",
            }

        # 4. Verificar logs de auditoría
        recent_logs = AuditLogger.get_recent_logs(5)  # Últimos 5 minutos
        error_rate = len(
            [log for log in recent_logs if log["status_code"] >= 400]
        ) / max(len(recent_logs), 1)

        checks["audit_logs"] = {
            "status": "healthy" if error_rate < 0.5 else "warning",
            "message": f"Error rate: {error_rate:.2%}",
            "recent_requests": len(recent_logs),
            "error_rate": error_rate,
        }

        # Estado general
        overall_status = "healthy"
        if any(check["status"] == "unhealthy" for check in checks.values()):
            overall_status = "unhealthy"
        elif any(check["status"] == "warning" for check in checks.values()):
            overall_status = "warning"

        return {
            "timestamp": datetime.now().isoformat(),
            "status": overall_status,
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "healthy_checks": len(
                    [c for c in checks.values() if c["status"] == "healthy"]
                ),
                "warning_checks": len(
                    [c for c in checks.values() if c["status"] == "warning"]
                ),
                "unhealthy_checks": len(
                    [c for c in checks.values() if c["status"] == "unhealthy"]
                ),
            },
        }

    except Exception as e:
        logger.error(f"Error en health check detallado: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }


@router.post("/clear-logs")
async def limpiar_logs_auditoria():
    """
    🧹 Limpiar logs de auditoría
    """
    try:
        # Limpiar logs
        audit_logs.clear()
        error_patterns.clear()
        request_stats.clear()

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "message": "Audit logs cleared successfully",
        }

    except Exception as e:
        logger.error(f"Error limpiando logs: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }


def _generate_dashboard_recommendations(
    auth_analysis: Dict, user_stats: Dict
) -> List[str]:
    """Generar recomendaciones basadas en el análisis del dashboard"""
    recommendations = []

    # Análisis de tasa de error
    error_rate = auth_analysis.get("error_rate", 0)
    if error_rate > 50:
        recommendations.append(
            "🚨 Tasa de error muy alta (>50%) - Revisar configuración de autenticación"
        )
    elif error_rate > 20:
        recommendations.append(
            "⚠️ Tasa de error elevada (>20%) - Monitorear logs de autenticación"
        )

    # Análisis de usuarios
    if user_stats.get("admin_users", 0) == 0:
        recommendations.append(
            "👤 No hay usuarios administradores - Crear usuario admin"
        )

    if user_stats.get("active_users", 0) == 0:
        recommendations.append(
            "⚠️ No hay usuarios activos - Verificar estado de usuarios"
        )

    # Recomendaciones generales
    if not recommendations:
        recommendations.append("✅ Sistema funcionando correctamente")

    return recommendations


# Nota: Middleware removido - APIRouter no soporta middleware directamente
# El middleware debe ser agregado a la aplicación principal en main.py
