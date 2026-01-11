"""
Utilidades centralizadas para manejo de errores en reportes
Evita exposición de detalles internos y proporciona mensajes consistentes
"""

import logging
from typing import Optional

from fastapi import HTTPException

logger = logging.getLogger(__name__)


def handle_report_error(e: Exception, operation: str, expose_details: bool = False) -> HTTPException:
    """
    Maneja errores de forma centralizada para reportes.
    
    Args:
        e: Excepción capturada
        operation: Descripción de la operación que falló (ej: "generar reporte de cartera")
        expose_details: Si True, expone detalles del error (solo para desarrollo)
    
    Returns:
        HTTPException con mensaje apropiado
    """
    error_type = type(e).__name__
    error_message = str(e)
    
    # Log detallado siempre (para debugging)
    logger.error(f"Error en {operation}: {error_type}: {error_message}", exc_info=True)
    
    # Determinar código de estado HTTP apropiado
    status_code = 500
    if isinstance(e, HTTPException):
        status_code = e.status_code
        detail = e.detail
    elif "does not exist" in error_message.lower() or "no such column" in error_message.lower():
        status_code = 500
        detail = (
            "Error de esquema de base de datos. "
            "Es posible que falten migraciones. "
            "Ejecuta: alembic upgrade head"
        )
    elif "timeout" in error_message.lower() or "timed out" in error_message.lower():
        status_code = 504
        detail = f"Timeout al {operation}. La consulta está tomando demasiado tiempo."
    elif "connection" in error_message.lower() or "pool" in error_message.lower():
        status_code = 503
        detail = f"Error de conexión al {operation}. Intenta nuevamente."
    elif "permission" in error_message.lower() or "forbidden" in error_message.lower():
        status_code = 403
        detail = "No tienes permisos para realizar esta operación."
    elif "not found" in error_message.lower() or "404" in error_message.lower():
        status_code = 404
        detail = "Recurso no encontrado."
    else:
        # Error genérico - no exponer detalles en producción
        if expose_details:
            detail = f"Error al {operation}: {error_message[:200]}"
        else:
            detail = f"Error al {operation}. Por favor, intente nuevamente o contacte al administrador."
    
    return HTTPException(status_code=status_code, detail=detail)


def validate_date_range(fecha_inicio, fecha_fin, max_days: Optional[int] = 365):
    """
    Valida que un rango de fechas sea válido.
    
    Args:
        fecha_inicio: Fecha de inicio
        fecha_fin: Fecha de fin
        max_days: Número máximo de días permitidos (None para sin límite)
    
    Raises:
        HTTPException si el rango es inválido
    """
    if fecha_inicio > fecha_fin:
        raise HTTPException(
            status_code=400,
            detail="La fecha de inicio debe ser anterior o igual a la fecha de fin"
        )
    
    if max_days is not None:
        from datetime import timedelta
        if fecha_fin - fecha_inicio > timedelta(days=max_days):
            raise HTTPException(
                status_code=400,
                detail=f"El rango de fechas no puede exceder {max_days} días. Por favor, seleccione un rango más corto."
            )
