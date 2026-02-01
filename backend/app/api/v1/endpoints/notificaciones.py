"""
Endpoints de notificaciones (stub para que el frontend no reciba 404).
GET /notificaciones/estadisticas/resumen para sidebar y contadores.
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/estadisticas/resumen")
def get_notificaciones_resumen():
    """
    Resumen de estadísticas de notificaciones. El frontend espera: no_leidas, total.
    """
    return {
        "no_leidas": 0,
        "total": 0,
    }
