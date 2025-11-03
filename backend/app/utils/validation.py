"""
Utilidades centralizadas de validación
Evita duplicación de lógica de validación en endpoints
"""

from typing import Any, Optional

from fastapi import HTTPException, Path, Query, status


def validate_positive_int(value: int, field_name: str = "id") -> int:
    """
    Validar que un entero sea positivo

    Args:
        value: Valor a validar
        field_name: Nombre del campo para mensaje de error

    Returns:
        int: Valor validado

    Raises:
        HTTPException: Si el valor no es positivo
    """
    if value <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} debe ser un número positivo mayor que 0",
        )
    return value


def validate_pagination(page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=100)) -> tuple[int, int]:
    """
    Validar y normalizar parámetros de paginación

    Args:
        page: Página actual (default: 1, mínimo: 1)
        per_page: Elementos por página (default: 20, mínimo: 1, máximo: 100)

    Returns:
        tuple[int, int]: (skip, limit) para usar en queries
    """
    skip = (page - 1) * per_page
    return skip, per_page


def path_id_gt_zero(id_value: int = Path(..., gt=0, description="ID del recurso")) -> int:
    """
    Helper para validar ID en path parameters

    Uso:
        @router.get("/{id}")
        def get_resource(id: int = Depends(path_id_gt_zero)):
            ...
    """
    return id_value


def validate_date_range(
    fecha_inicio: Optional[Any] = None,
    fecha_fin: Optional[Any] = None,
) -> tuple[Optional[Any], Optional[Any]]:
    """
    Validar rango de fechas

    Args:
        fecha_inicio: Fecha de inicio
        fecha_fin: Fecha de fin

    Returns:
        tuple: (fecha_inicio, fecha_fin) validadas

    Raises:
        HTTPException: Si fecha_inicio > fecha_fin
    """
    if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="fecha_inicio no puede ser mayor que fecha_fin",
        )
    return fecha_inicio, fecha_fin


def validate_limit(limit: int = Query(20, ge=1, le=1000, description="Límite de resultados")) -> int:
    """
    Validar límite de resultados

    Args:
        limit: Límite de resultados (default: 20, min: 1, max: 1000)

    Returns:
        int: Límite validado
    """
    return limit


def validate_offset(
    page: int = Query(1, ge=1, description="Número de página"), per_page: int = Query(20, ge=1, le=100)
) -> int:
    """
    Calcular offset para paginación

    Args:
        page: Página actual
        per_page: Elementos por página

    Returns:
        int: Offset calculado
    """
    return (page - 1) * per_page
