"""
Endpoint de Análisis de Impacto en Performance
Proporciona métricas y análisis de impacto del sistema
"""

import logging
import time
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.core.impact_monitoring import get_impact_analyzer
from app.core.error_impact_analysis import get_error_analyzer
from app.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health", response_model=Dict[str, Any])
async def get_health_impact_analysis_public():
    """
    Obtener análisis de impacto de health checks (PÚBLICO)

    - Métricas de performance de health checks
    - Impacto en recursos del sistema
    - Alertas y recomendaciones
    """
    try:
        analyzer = get_impact_analyzer()
        status_data = analyzer.get_current_status()

        return {"status": "success", "data": status_data, "timestamp": time.time()}
    except Exception as e:
        logger.error(f"Error obteniendo análisis de health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo análisis de health: {str(e)}",
        )


@router.get("/impact/health", response_model=Dict[str, Any])
async def get_health_impact_analysis(current_user: User = Depends(get_current_user)):
    """
    Obtener análisis de impacto de health checks

    - Métricas de performance de health checks
    - Impacto en recursos del sistema
    - Alertas y recomendaciones
    """
    try:
        analyzer = get_impact_analyzer()
        status_data = analyzer.get_current_status()

        return {"status": "success", "data": status_data, "timestamp": time.time()}
    except Exception as e:
        logger.error(f"Error obteniendo análisis de health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo análisis de health: {str(e)}",
        )


@router.get("/impact/performance", response_model=Dict[str, Any])
async def get_performance_impact_analysis(
    current_user: User = Depends(get_current_user),
):
    """
    Obtener análisis de impacto en performance

    - Métricas de performance de endpoints
    - Análisis de impacto en recursos
    - Recomendaciones de optimización
    """
    try:
        analyzer = get_impact_analyzer()
        report = analyzer.get_performance_report()

        return {"status": "success", "data": report, "timestamp": time.time()}
    except Exception as e:
        logger.error(f"Error obteniendo análisis de performance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo análisis de performance: {str(e)}",
        )


@router.get("/impact/errors", response_model=Dict[str, Any])
async def get_error_impact_analysis(current_user: User = Depends(get_current_user)):
    """
    Obtener análisis de impacto de errores

    - Tasa de error del sistema
    - Análisis de impacto de errores
    - Estado de circuit breakers
    - Recomendaciones de manejo de errores
    """
    try:
        analyzer = get_error_analyzer()
        analysis = analyzer.get_error_impact_analysis()
        summary = analyzer.get_endpoint_error_summary()
        recent_errors = analyzer.get_recent_errors(limit=10)

        return {
            "status": "success",
            "data": {
                "impact_analysis": analysis.__dict__,
                "endpoint_summary": summary,
                "recent_errors": recent_errors,
            },
            "timestamp": time.time(),
        }
    except Exception as e:
        logger.error(f"Error obteniendo análisis de errores: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo análisis de errores: {str(e)}",
        )


@router.get("/impact/comprehensive", response_model=Dict[str, Any])
async def get_comprehensive_impact_analysis(
    current_user: User = Depends(get_current_user),
):
    """
    Obtener análisis integral de impacto del sistema

    - Health checks impact
    - Performance impact
    - Error impact
    - System recommendations
    """
    try:
        # Obtener análisis de cada componente
        health_analyzer = get_impact_analyzer()
        error_analyzer = get_error_analyzer()

        health_status = health_analyzer.get_current_status()
        performance_report = health_analyzer.get_performance_report()
        error_analysis = error_analyzer.get_error_impact_analysis()
        error_summary = error_analyzer.get_endpoint_error_summary()

        # Calcular score general del sistema
        system_score = _calculate_system_score(health_status, performance_report, error_analysis)

        # Generar recomendaciones generales
        general_recommendations = _generate_general_recommendations(health_status, performance_report, error_analysis)

        return {
            "status": "success",
            "data": {
                "system_score": system_score,
                "health_analysis": health_status,
                "performance_analysis": performance_report,
                "error_analysis": {
                    "impact_analysis": error_analysis.__dict__,
                    "endpoint_summary": error_summary,
                },
                "general_recommendations": general_recommendations,
                "analysis_timestamp": time.time(),
            },
            "timestamp": time.time(),
        }
    except Exception as e:
        logger.error(f"Error obteniendo análisis integral: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo análisis integral: {str(e)}",
        )


@router.post("/impact/monitoring/start")
async def start_impact_monitoring(current_user: User = Depends(get_current_user)):
    """
    Iniciar monitoreo de impacto del sistema

    Requiere permisos de administrador
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de administrador",
        )

    try:
        analyzer = get_impact_analyzer()
        analyzer.start_monitoring()

        return {
            "status": "success",
            "message": "Monitoreo de impacto iniciado",
            "timestamp": time.time(),
        }
    except Exception as e:
        logger.error(f"Error iniciando monitoreo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error iniciando monitoreo: {str(e)}",
        )


@router.post("/impact/monitoring/stop")
async def stop_impact_monitoring(current_user: User = Depends(get_current_user)):
    """
    Detener monitoreo de impacto del sistema

    Requiere permisos de administrador
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de administrador",
        )

    try:
        analyzer = get_impact_analyzer()
        analyzer.stop_monitoring()

        return {
            "status": "success",
            "message": "Monitoreo de impacto detenido",
            "timestamp": time.time(),
        }
    except Exception as e:
        logger.error(f"Error deteniendo monitoreo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deteniendo monitoreo: {str(e)}",
        )


def _calculate_system_score(health_status: Dict, performance_report: Dict, error_analysis: Any) -> Dict[str, Any]:
    """Calcular score general del sistema"""
    score = 100

    # Penalizar por alertas de health
    if health_status.get("active_alerts", 0) > 0:
        score -= health_status["active_alerts"] * 10

    # Penalizar por performance
    if performance_report.get("performance_summary", {}).get("avg_response_time_ms", 0) > 500:
        score -= 20

    # Penalizar por tasa de error
    if error_analysis.error_rate > 0.05:  # 5%
        score -= error_analysis.error_rate * 200

    # Penalizar por errores consecutivos
    if error_analysis.consecutive_errors > 3:
        score -= error_analysis.consecutive_errors * 5

    score = max(0, min(100, score))

    # Determinar nivel
    if score >= 90:
        level = "EXCELLENT"
    elif score >= 80:
        level = "GOOD"
    elif score >= 70:
        level = "FAIR"
    elif score >= 60:
        level = "POOR"
    else:
        level = "CRITICAL"

    return {
        "score": score,
        "level": level,
        "factors": {
            "health_alerts": health_status.get("active_alerts", 0),
            "avg_response_time": performance_report.get("performance_summary", {}).get("avg_response_time_ms", 0),
            "error_rate": error_analysis.error_rate,
            "consecutive_errors": error_analysis.consecutive_errors,
        },
    }


def _generate_general_recommendations(health_status: Dict, performance_report: Dict, error_analysis: Any) -> list:
    """Generar recomendaciones generales del sistema"""
    recommendations = []

    # Recomendaciones basadas en health
    if health_status.get("active_alerts", 0) > 0:
        recommendations.append("Revisar alertas activas del sistema")

    # Recomendaciones basadas en performance
    avg_response_time = performance_report.get("performance_summary", {}).get("avg_response_time_ms", 0)
    if avg_response_time > 1000:
        recommendations.append("Optimizar endpoints con tiempo de respuesta > 1s")

    # Recomendaciones basadas en errores
    if error_analysis.error_rate > 0.05:
        recommendations.append("Implementar manejo de errores más robusto")

    if error_analysis.consecutive_errors > 3:
        recommendations.append("Activar circuit breakers para endpoints problemáticos")

    if not recommendations:
        recommendations.append("Sistema funcionando dentro de parámetros normales")

    return recommendations
