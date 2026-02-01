"""
Endpoints de clientes (stub para que el frontend no reciba 404).
GET /clientes (listado paginado) y GET /clientes/stats hasta tener BD real.
"""
from fastapi import APIRouter, Query

router = APIRouter()


@router.get("", summary="Listado paginado")
@router.get("/", include_in_schema=False)
def get_clientes(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """
    Listado paginado de clientes. El frontend espera:
    clientes (array), total, page, per_page, total_pages.
    """
    return {
        "clientes": [],
        "total": 0,
        "page": page,
        "per_page": per_page,
        "total_pages": 0,
    }


@router.get("/stats")
def get_clientes_stats():
    """
    Estadísticas de clientes. El frontend espera:
    total, activos, inactivos, finalizados.
    """
    return {
        "total": 0,
        "activos": 0,
        "inactivos": 0,
        "finalizados": 0,
    }
