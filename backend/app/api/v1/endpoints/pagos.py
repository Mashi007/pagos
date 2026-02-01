"""
Endpoints de pagos (stub para que el frontend no reciba 404).
GET /pagos/kpis y GET /pagos/stats con datos mínimos hasta tener BD/negocio real.
"""
from typing import List, Optional

from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/kpis")
def get_pagos_kpis(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
):
    """
    KPIs de pagos. El frontend espera: cuotas_pendientes, clientes_en_mora,
    montoCobradoMes, saldoPorCobrar, clientesAlDia (y opcionales).
    """
    return {
        "cuotas_pendientes": 0,
        "clientes_en_mora": 0,
        "montoCobradoMes": 0,
        "saldoPorCobrar": 0,
        "clientesAlDia": 0,
    }


@router.get("/stats")
def get_pagos_stats(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
):
    """
    Estadísticas de pagos por estado. El frontend espera:
    total_pagos, total_pagado, pagos_por_estado: [{ estado, count }],
    cuotas_pagadas, cuotas_pendientes, cuotas_atrasadas, pagos_hoy.
    Stub hasta tener BD/negocio real.
    """
    return {
        "total_pagos": 0,
        "total_pagado": 0,
        "pagos_por_estado": [],
        "cuotas_pagadas": 0,
        "cuotas_pendientes": 0,
        "cuotas_atrasadas": 0,
        "pagos_hoy": 0,
    }
