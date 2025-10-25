from collections import deque
import statistics
﻿"""Dashboard de Diagnóstico en Tiempo Real
Sistema de monitoreo y auditoría para problemas de autenticación
"""

import logging
from collections import defaultdict, deque
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Request, Response, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

# Almacenamiento en memoria para auditoría
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
        log_entry = {
            "method": request.method,
            "url": str(request.url),
            "status_code": response.status_code,
            "user_id": user_id,
            "user_agent": request.headers.get("user-agent", "unknown"),
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
                "🔒 401 Unauthorized - "
                + f"{request.method} {request.url} "
                + f"- Error: {error}"
            )

    @staticmethod
    def get_recent_logs(minutes: int = 60) -> List[Dict[str, Any]]:
        """Obtener logs recientes"""
        return [
            log for log in audit_logs
        ]

    @staticmethod
    def get_error_summary() -> Dict[str, Any]:
        """Obtener resumen de errores"""
        return {
            "total_errors": sum(error_patterns.values()),
            "error_patterns": dict(error_patterns),
            "request_stats": dict(request_stats),
            "recent_401_errors": [
                log for log in audit_logs
                if log["status_code"] == 401
        }

# ============================================
# ENDPOINTS DEL DASHBOARD
# ============================================

@router.get("/dashboard/overview")
async def get_dashboard_overview(
    db: Session = Depends(get_db),
):
    """Obtener vista general del dashboard"""
    try:
        # Obtener estadísticas de auditoría
        audit_summary = AuditLogger.get_error_summary()

        # Obtener logs recientes
        recent_logs = AuditLogger.get_recent_logs(60)

        # Calcular métricas básicas
        total_requests = len(recent_logs)
        error_requests = len([log for log in recent_logs if log["status_code"] >= 400])
        auth_requests = len([log for log in recent_logs if log["auth_header_present"]])

        overview = {
            "metrics": {
                "total_requests_last_hour": total_requests,
                "error_requests_last_hour": error_requests,
                "auth_requests_last_hour": auth_requests,
                "error_rate": (error_requests / total_requests * 100) if total_requests > 0 else 0,
            },
            "audit_summary": audit_summary,
            "system_status": "operational",
            "database_status": "connected",
        }

        return {
            "success": True,
            "overview": overview
        }

    except Exception as e:
        logger.error(f"Error obteniendo vista general: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )

@router.get("/dashboard/recent-activity")
async def get_recent_activity(
    minutes: int = 30,
    db: Session = Depends(get_db),
):
    """Obtener actividad reciente"""
    try:
        recent_logs = AuditLogger.get_recent_logs(minutes)

        # Procesar logs para actividad
        activity = []
        for log in recent_logs:
            activity.append({
                "method": log["method"],
                "url": log["url"],
                "status_code": log["status_code"],
                "user_id": log["user_id"],
                "ip": log["ip"],
                "error": log["error"],
                "auth_required": log["auth_header_present"]
            })

        return {
            "success": True,
            "activity": activity,
            "total_events": len(activity),
        }

    except Exception as e:
        logger.error(f"Error obteniendo actividad reciente: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )

@router.get("/dashboard/error-analysis")
async def get_error_analysis(
    db: Session = Depends(get_db),
):
    """Obtener análisis de errores"""
    try:
        audit_summary = AuditLogger.get_error_summary()

        # Analizar patrones de error
        error_analysis = {
            "error_patterns": audit_summary["error_patterns"],
            "request_statistics": audit_summary["request_stats"],
            "recent_401_errors": audit_summary["recent_401_errors"],
            "recommendations": []
        }

        # Generar recomendaciones basadas en patrones
        if error_patterns.get("Invalid token", 0) > 10:
            error_analysis["recommendations"].append(
            )

        if error_patterns.get("Token expired", 0) > 5:
            error_analysis["recommendations"].append(
            )

        if not error_analysis["recommendations"]:
            error_analysis["recommendations"].append(
                "Sistema funcionando normalmente"
            )

        return {
            "success": True,
            "error_analysis": error_analysis
        }

    except Exception as e:
        logger.error(f"Error analizando errores: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )

async def log_dashboard_event(
    event_data: Dict[str, Any],
    request: Request,
    db: Session = Depends(get_db),
):
    """Registrar evento en el dashboard"""
    try:
        # Crear respuesta simulada para el logger
        from fastapi import Response
        response = Response()
        response.status_code = event_data.get("status_code", 200)

        # Registrar evento
        AuditLogger.log_request(
            request=request,
            response=response,
            user_id=event_data.get("user_id"),
            error=event_data.get("error")
        )

        return {
            "success": True,
        }

    except Exception as e:
        logger.error(f"Error registrando evento: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )

@router.get("/dashboard/system-health")
async def get_system_health(
    db: Session = Depends(get_db),
):
    """Obtener estado de salud del sistema"""
    try:
        # Verificar conexión a BD
        db_status = "connected"
        try:
            db.execute("SELECT 1")
        except Exception:
            db_status = "disconnected"

        # Obtener métricas del sistema
        recent_logs = AuditLogger.get_recent_logs(60)
        error_rate = len([log for log in recent_logs if log["status_code"] >= 400]) / max(len(recent_logs), 1) * 100

        health_status = {
            "overall_status": "healthy" if error_rate < 10 and db_status == "connected" else "degraded",
            "components": {
                "database": db_status,
                "authentication": "operational",
                "api_endpoints": "operational"
            },
            "metrics": {
                "error_rate_percent": round(error_rate, 2),
                "total_requests_last_hour": len(recent_logs),
            },
            "alerts": []
        }

        # Agregar alertas si es necesario
        if error_rate > 20:
            health_status["alerts"].append({
                "type": "high_error_rate",
                "message": f"Tasa de error alta: {error_rate:.1f}%",
                "severity": "warning"
            })

        if db_status == "disconnected":
            health_status["alerts"].append({
                "type": "database_disconnected",
                "severity": "critical"
            })

        return {
            "success": True,
            "health_status": health_status
        }

    except Exception as e:
        logger.error(f"Error obteniendo estado de salud: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )
