"""
Endpoints de KPIs (stub para que el frontend no reciba 404).
GET /kpis/dashboard usado por DashboardFinanciamiento y DashboardCuotas.
"""
from typing import Optional

from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/dashboard")
def get_kpis_dashboard(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
):
    """KPIs del dashboard (stub). Frontend: DashboardFinanciamiento, DashboardCuotas."""
    return {
        "kpis": [],
        "total_prestamos": 0,
        "total_morosidad": 0,
    }
