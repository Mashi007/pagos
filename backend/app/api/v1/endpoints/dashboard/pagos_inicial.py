"""
Carga inicial del dashboard de Pagos: una sola peticion HTTP reutiliza la misma logica
que GET /pagos/stats, /pagos/kpis, /dashboard/opciones-filtros y /dashboard/evolucion-pagos.
Los endpoints individuales se mantienen sin cambios.

Las consultas se ejecutan en paralelo (un Session de SQLAlchemy por hilo) para reducir
latencia total del endpoint.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter, Depends, Query

from app.core.database import SessionLocal
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
):
    """
    Agrega datos para la primera pintura del dashboard de pagos (menos round-trips).

    No usa la sesión inyectada de `get_db`: cada bloque de lectura abre su propia sesión
    en un hilo (SQLAlchemy Session no es thread-safe).
    """
    # Import diferido para evitar ciclos de importacion al cargar modulos.
    from app.api.v1.endpoints.pagos import get_pagos_kpis, get_pagos_stats
    from app.api.v1.endpoints.dashboard.graficos import (
        get_cuotas_con_pago_aplicado_por_mes_cuota,
        get_evolucion_pagos,
    )
    from app.api.v1.endpoints.dashboard.kpis import get_opciones_filtros

    def job_opciones() -> Tuple[str, Any]:
        s = SessionLocal()
        try:
            return "opciones", get_opciones_filtros(db=s)
        finally:
            s.close()

    def job_stats() -> Tuple[str, Any]:
        s = SessionLocal()
        try:
            return (
                "stats",
                get_pagos_stats(
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin,
                    analista=analista,
                    concesionario=concesionario,
                    modelo=modelo,
                    db=s,
                ),
            )
        finally:
            s.close()

    def job_kpis() -> Tuple[str, Any]:
        s = SessionLocal()
        try:
            return (
                "kpis",
                get_pagos_kpis(
                    mes=None,
                    anio=None,
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin,
                    db=s,
                ),
            )
        finally:
            s.close()

    def job_evolucion() -> Tuple[str, Any]:
        s = SessionLocal()
        try:
            ev = get_evolucion_pagos(
                fecha_inicio=fecha_inicio,
                meses=meses_evolucion,
                analista=analista,
                concesionario=concesionario,
                modelo=modelo,
                db=s,
            )
            return "evolucion", ev
        finally:
            s.close()

    def job_cuotas() -> Tuple[str, Any]:
        s = SessionLocal()
        try:
            cu = get_cuotas_con_pago_aplicado_por_mes_cuota(
                meses=meses_evolucion,
                analista=analista,
                concesionario=concesionario,
                modelo=modelo,
                db=s,
            )
            return "cuotas", cu
        finally:
            s.close()

    out: Dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [
            pool.submit(job_opciones),
            pool.submit(job_stats),
            pool.submit(job_kpis),
            pool.submit(job_evolucion),
            pool.submit(job_cuotas),
        ]
        for fut in as_completed(futures):
            key, val = fut.result()
            out[key] = val

    return {
        "opciones_filtros": out["opciones"],
        "pagos_stats": out["stats"],
        "kpis_pagos": out["kpis"],
        "evolucion_pagos_meses": out["evolucion"].get("meses", []),
        "cuotas_con_pago_aplicado_por_mes_cuota": out["cuotas"].get("meses", []),
    }
