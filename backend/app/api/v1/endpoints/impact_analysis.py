"""Endpoint de Análisis de Impacto en Performance
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

        return {
            "status": "success",
            "data": status_data,
            "timestamp": time.time(),
        }
    except Exception as e:
        logger.error(f"Error obteniendo análisis de health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo análisis de health: {str(e)}",
        )

@router.get("/impact/health", response_model=Dict[str, Any])
async def get_health_impact_analysis(
    current_user: User = Depends(get_current_user),
):
    """
    Obtener análisis de impacto de health checks
    - Métricas de performance de health checks
    - Impacto en recursos del sistema
    - Alertas y recomendaciones
    """
    try:
        analyzer = get_impact_analyzer()
        status_data = analyzer.get_current_status()

        return {
            "status": "success",
            "data": status_data,
            "timestamp": time.time(),
        }
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

        return {
            "status": "success",
            "data": report,
            "timestamp": time.time(),
        }
    except Exception as e:
        logger.error(f"Error obteniendo análisis de performance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo análisis de performance: {str(e)}",
        )

@router.get("/impact/errors", response_model=Dict[str, Any])
async def get_error_impact_analysis(
    current_user: User = Depends(get_current_user),
):
    """
    Obtener análisis de impacto de errores
    - Análisis de errores críticos
    - Impacto en disponibilidad del sistema
    - Recomendaciones de mitigación
    """
    try:
        error_analyzer = get_error_analyzer()
        error_report = error_analyzer.get_error_impact_report()

        return {
            "status": "success",
            "data": error_report,
            "timestamp": time.time(),
        }
    except Exception as e:
        logger.error(f"Error obteniendo análisis de errores: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo análisis de errores: {str(e)}",
        )

@router.get("/impact/resource-usage", response_model=Dict[str, Any])
async def get_resource_usage_impact(
    current_user: User = Depends(get_current_user),
):
    """
    Obtener análisis de impacto en uso de recursos
    - Uso de CPU y memoria
    - Impacto en base de datos
    - Recomendaciones de escalado
    """
    try:
        analyzer = get_impact_analyzer()
        resource_report = analyzer.get_resource_usage_report()

        return {
            "status": "success",
            "data": resource_report,
            "timestamp": time.time(),
        }
    except Exception as e:
        logger.error(f"Error obteniendo análisis de recursos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo análisis de recursos: {str(e)}",
        )

@router.get("/impact/endpoints", response_model=Dict[str, Any])
async def get_endpoints_impact_analysis(
    current_user: User = Depends(get_current_user),
):
    """
    Obtener análisis de impacto por endpoint
    - Métricas de performance por endpoint
    - Identificación de endpoints problemáticos
    - Recomendaciones específicas
    """
    try:
        analyzer = get_impact_analyzer()
        endpoints_report = analyzer.get_endpoints_impact_report()

        return {
            "status": "success",
            "data": endpoints_report,
            "timestamp": time.time(),
        }
    except Exception as e:
        logger.error(f"Error obteniendo análisis de endpoints: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo análisis de endpoints: {str(e)}",
        )

@router.get("/impact/summary", response_model=Dict[str, Any])
async def get_impact_summary(
    current_user: User = Depends(get_current_user),
):
    """
    Obtener resumen general de impacto
    - Resumen de todas las métricas
    - Estado general del sistema
    - Recomendaciones prioritarias
    """
    try:
        analyzer = get_impact_analyzer()
        error_analyzer = get_error_analyzer()

        # Obtener datos de ambos analizadores
        performance_data = analyzer.get_current_status()
        error_data = error_analyzer.get_error_impact_report()

        # Crear resumen consolidado
        summary = {
            "timestamp": time.time(),
            "overall_status": "operational",
            "performance_metrics": performance_data,
            "error_metrics": error_data,
            "recommendations": [],
            "critical_issues": [],
        }

        # Generar recomendaciones basadas en los datos
        if performance_data.get("avg_response_time", 0) > 2000:
            summary["recommendations"].append(
                "Tiempo de respuesta alto - considerar optimización"
            )

        if error_data.get("error_rate", 0) > 5:
            summary["critical_issues"].append(
                "Tasa de error alta - requiere atención inmediata"
            )

        if not summary["recommendations"]:
            summary["recommendations"].append("Sistema funcionando dentro de parámetros normales")

        return {
            "status": "success",
            "data": summary,
        }

    except Exception as e:
        logger.error(f"Error obteniendo resumen de impacto: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo resumen de impacto: {str(e)}",
        )
