"""
Helpers centralizados para validación consistente en todos los endpoints
"""
from datetime import date
from typing import Optional

from fastapi import HTTPException, Query
from pydantic import Field

from app.utils.validators import (
    sanitize_sql_input,
    validate_date_range_safe,
    validate_numeric_range,
)


def validate_query_string(
    value: Optional[str],
    param_name: str,
    max_length: int = 100,
    required: bool = False,
) -> Optional[str]:
    """
    Valida y sanitiza un parámetro de query string.
    
    Args:
        value: Valor a validar
        param_name: Nombre del parámetro para mensajes de error
        max_length: Longitud máxima permitida
        required: Si es requerido
    
    Returns:
        Valor sanitizado
    
    Raises:
        HTTPException: Si la validación falla
    """
    if value is None:
        if required:
            raise HTTPException(status_code=400, detail=f"{param_name} es requerido")
        return None
    
    try:
        return sanitize_sql_input(value, max_length=max_length)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"{param_name}: {str(e)}")


def validate_query_int(
    value: Optional[int],
    param_name: str,
    min_val: int,
    max_val: int,
    default: Optional[int] = None,
) -> int:
    """
    Valida un parámetro entero de query.
    
    Args:
        value: Valor a validar
        param_name: Nombre del parámetro
        min_val: Valor mínimo
        max_val: Valor máximo
        default: Valor por defecto si es None
    
    Returns:
        Valor validado
    
    Raises:
        HTTPException: Si la validación falla
    """
    if value is None:
        if default is not None:
            return default
        raise HTTPException(status_code=400, detail=f"{param_name} es requerido")
    
    try:
        return validate_numeric_range(value, min_val, max_val, param_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def validate_query_dates(
    fecha_inicio: Optional[date],
    fecha_fin: Optional[date],
    max_days: int = 1825,
    required: bool = False,
) -> tuple[Optional[date], Optional[date]]:
    """
    Valida un rango de fechas de query.
    
    Args:
        fecha_inicio: Fecha de inicio
        fecha_fin: Fecha de fin
        max_days: Máximo de días permitidos
        required: Si ambas fechas son requeridas
    
    Returns:
        Tupla (fecha_inicio, fecha_fin) validadas
    
    Raises:
        HTTPException: Si la validación falla
    """
    if fecha_inicio is None or fecha_fin is None:
        if required:
            raise HTTPException(
                status_code=400, detail="fecha_inicio y fecha_fin son requeridas"
            )
        return fecha_inicio, fecha_fin
    
    try:
        return validate_date_range_safe(fecha_inicio, fecha_fin, max_days=max_days)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Query parameters helpers para FastAPI
def QueryString(
    default: Optional[str] = None,
    param_name: str = "param",
    max_length: int = 100,
    required: bool = False,
    description: str = "",
):
    """
    Helper para crear Query parameters de tipo string con validación.
    
    Usage:
        analista: Optional[str] = QueryString(
            default=None,
            param_name="analista",
            max_length=100,
            description="Filtrar por analista"
        )
    """
    return Query(
        default=default,
        description=description,
        ge=None if not required else 1,
        max_length=max_length,
    )


def QueryInt(
    default: Optional[int] = None,
    param_name: str = "param",
    min_val: int = 1,
    max_val: int = 1000,
    description: str = "",
):
    """
    Helper para crear Query parameters de tipo int con validación.
    
    Usage:
        semanas: int = QueryInt(
            default=12,
            param_name="semanas",
            min_val=1,
            max_val=52,
            description="Número de semanas"
        )
    """
    return Query(
        default=default,
        description=description,
        ge=min_val,
        le=max_val,
    )
