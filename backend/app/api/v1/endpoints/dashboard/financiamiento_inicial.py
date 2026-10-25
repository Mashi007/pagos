"""
Carga inicial del dashboard de Financiamiento: reduce round-trips agrupando
opciones de filtros, KPIs planos (/kpis/dashboard) y tendencia mensual.
El endpoint /dashboard/prestamos-por-concesionario se mantiene aparte (formato especifico).
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])


def _compute_financiamiento_dashboard_inicial(
    db: Session,
    *,
    fecha_inicio: Optional[str],
    fecha_fin: Optional[str],
    analista: Optional[str],
    concesionario: Optional[str],
    modelo: Optional[str],
    meses_tendencia: int,
) -> dict:
    from app.api.v1.endpoints.dashboard.graficos import get_financiamiento_tendencia_mensual
    from app.api.v1.endpoints.dashboard.kpis import get_kpis_dashboard, get_opciones_filtros

    opciones = get_opciones_filtros(db=db)
    kpis = get_kpis_dashboard(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        analista=analista,
        concesionario=concesionario,
        modelo=modelo,
        db=db,
    )
    tendencia = get_financiamiento_tendencia_mensual(
        fecha_inicio=fecha_inicio,
        meses=meses_tendencia,
        analista=analista,
        concesionario=concesionario,
        modelo=modelo,
        db=db,
    )
    return {
        "opciones_filtros": opciones,
        "kpis_dashboard": kpis,
        "tendencia_mensual_meses": tendencia.get("meses", []),
    }


@router.get("/financiamiento-inicial")
def get_financiamiento_dashboard_inicial(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    meses_tendencia: int = Query(12, ge=1, le=24),
    db: Session = Depends(get_db),
):
    from app.api.v1.endpoints.dashboard.utils import menu_grafico_cached

    return menu_grafico_cached(
        "financiamiento-inicial",
        lambda: _compute_financiamiento_dashboard_inicial(
            db,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            analista=analista,
            concesionario=concesionario,
            modelo=modelo,
            meses_tendencia=meses_tendencia,
        ),
        fecha_inicio=fecha_inicio or "",
        fecha_fin=fecha_fin or "",
        analista=analista or "",
        concesionario=concesionario or "",
        modelo=modelo or "",
        meses_tendencia=meses_tendencia,
    )
