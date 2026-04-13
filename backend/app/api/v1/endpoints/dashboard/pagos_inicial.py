"""
Carga inicial del dashboard de Pagos: una sola peticion HTTP reutiliza la misma logica
que GET /pagos/stats, /pagos/kpis, /dashboard/opciones-filtros y /dashboard/evolucion-pagos.
Los endpoints individuales se mantienen sin cambios.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/pagos-inicial")
def get_pagos_dashboard_inicial(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    meses_evolucion: int = Query(6, ge=1, le=24),
    db: Session = Depends(get_db),
):
    """
    Agrega datos para la primera pintura del dashboard de pagos (menos round-trips).
    """
    # Import diferido para evitar ciclos de importacion al cargar modulos.
    from app.api.v1.endpoints.pagos import get_pagos_kpis, get_pagos_stats
    from app.api.v1.endpoints.dashboard.graficos import (
        get_cuotas_con_pago_aplicado_por_mes_cuota,
        get_evolucion_pagos,
    )
    from app.api.v1.endpoints.dashboard.kpis import get_opciones_filtros

    opciones = get_opciones_filtros(db=db)
    stats = get_pagos_stats(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        analista=analista,
        concesionario=concesionario,
        modelo=modelo,
        db=db,
    )
    kpis = get_pagos_kpis(
        mes=None,
        anio=None,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        db=db,
    )
    evolucion = get_evolucion_pagos(
        fecha_inicio=fecha_inicio,
        meses=meses_evolucion,
        analista=analista,
        concesionario=concesionario,
        modelo=modelo,
        db=db,
    )
    cuotas_aplicadas_mes = get_cuotas_con_pago_aplicado_por_mes_cuota(
        meses=meses_evolucion,
        analista=analista,
        concesionario=concesionario,
        modelo=modelo,
        db=db,
    )
    return {
        "opciones_filtros": opciones,
        "pagos_stats": stats,
        "kpis_pagos": kpis,
        "evolucion_pagos_meses": evolucion.get("meses", []),
        "cuotas_con_pago_aplicado_por_mes_cuota": cuotas_aplicadas_mes.get("meses", []),
    }
