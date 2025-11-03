"""
Utilidades para paginación estandarizada
Proporciona helpers para respuestas paginadas consistentes
"""

from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Response model estandarizado para paginación"""

    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    class Config:
        json_schema_extra = {
            "example": {
                "items": [],
                "total": 100,
                "page": 1,
                "page_size": 20,
                "total_pages": 5,
            }
        }


def create_paginated_response(
    items: List[Any],
    total: int,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    """
    Crea una respuesta paginada estandarizada

    Args:
        items: Lista de items de la página actual
        total: Total de items en la base de datos
        page: Página actual (1-indexed)
        page_size: Tamaño de la página

    Returns:
        dict: Respuesta paginada con estructura estandarizada
    """
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def calculate_pagination_params(
    page: Optional[int] = None,
    per_page: Optional[int] = None,
    skip: Optional[int] = None,
    limit: Optional[int] = None,
    default_page: int = 1,
    default_per_page: int = 20,
    max_per_page: int = 100,
) -> tuple[int, int]:
    """
    Calcula skip y limit a partir de parámetros de paginación
    Soporta tanto page/per_page como skip/limit

    Args:
        page: Número de página (1-indexed) - alternativo a skip
        per_page: Items por página - alternativo a limit
        skip: Registros a omitir - alternativo a page
        limit: Límite de registros - alternativo a per_page
        default_page: Página por defecto si no se especifica
        default_per_page: Items por página por defecto
        max_per_page: Máximo de items por página permitido

    Returns:
        tuple[int, int]: (skip, limit) para usar en queries

    Ejemplo:
        skip, limit = calculate_pagination_params(page=2, per_page=20)
        # Retorna: (20, 20)
    """
    # Si se especifica skip/limit, usarlos directamente
    if skip is not None and limit is not None:
        return max(0, skip), min(max(1, limit), max_per_page)

    # Si se especifica page/per_page, convertir a skip/limit
    if page is not None and per_page is not None:
        page = max(1, page)
        per_page = min(max(1, per_page), max_per_page)
        skip = (page - 1) * per_page
        return skip, per_page

    # Si solo se especifica page o skip
    if page is not None:
        page = max(1, page)
        skip = (page - 1) * default_per_page
        return skip, default_per_page

    if skip is not None:
        skip = max(0, skip)
        limit = limit if limit is not None else default_per_page
        return skip, min(max(1, limit), max_per_page)

    # Si solo se especifica per_page o limit
    if per_page is not None:
        per_page = min(max(1, per_page), max_per_page)
        return 0, per_page

    if limit is not None:
        limit = min(max(1, limit), max_per_page)
        return 0, limit

    # Valores por defecto
    return 0, default_per_page


def validate_pagination_query(
    page: Optional[int] = None,
    per_page: Optional[int] = None,
    skip: Optional[int] = None,
    limit: Optional[int] = None,
    default_page: int = 1,
    default_per_page: int = 20,
    max_per_page: int = 100,
) -> tuple[int, int, int]:
    """
    Valida y calcula parámetros de paginación
    Retorna page, skip, limit normalizados

    Args:
        page: Número de página (1-indexed)
        per_page: Items por página
        skip: Registros a omitir
        limit: Límite de registros
        default_page: Página por defecto
        default_per_page: Items por página por defecto
        max_per_page: Máximo permitido

    Returns:
        tuple[int, int, int]: (page, skip, limit) normalizados
    """
    skip, limit = calculate_pagination_params(
        page=page,
        per_page=per_page,
        skip=skip,
        limit=limit,
        default_page=default_page,
        default_per_page=default_per_page,
        max_per_page=max_per_page,
    )

    # Calcular page a partir de skip y limit
    calculated_page = (skip // limit) + 1 if limit > 0 else 1

    return calculated_page, skip, limit
