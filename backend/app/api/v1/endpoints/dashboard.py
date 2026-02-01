"""
Endpoints del dashboard (stub para que el frontend no reciba 404).
Todos los GET devuelven datos mínimos hasta tener BD/negocio real.
"""
from typing import Optional

from fastapi import APIRouter, Query

router = APIRouter()


def _kpi(valor: float = 0, variacion: float = 0) -> dict:
    return {"valor_actual": valor, "variacion_porcentual": variacion}


@router.get("/opciones-filtros")
def get_opciones_filtros():
    """Opciones para filtros: analistas, concesionarios, modelos."""
    return {
        "analistas": [],
        "concesionarios": [],
        "modelos": [],
    }


@router.get("/kpis-principales")
def get_kpis_principales(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
):
    """KPIs principales del dashboard."""
    return {
        "total_prestamos": _kpi(0),
        "creditos_nuevos_mes": _kpi(0),
        "total_clientes": _kpi(0),
        "clientes_por_estado": {
            "activos": _kpi(0),
            "inactivos": _kpi(0),
            "finalizados": _kpi(0),
        },
        "total_morosidad_usd": _kpi(0),
        "cuotas_programadas": {"valor_actual": 0},
        "porcentaje_cuotas_pagadas": 0,
    }


@router.get("/admin")
def get_dashboard_admin(
    periodo: Optional[str] = Query(None),
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
):
    """Dashboard admin: financieros, meta, evolucion_mensual."""
    return {
        "financieros": {
            "ingresosCapital": 0,
            "ingresosInteres": 0,
            "ingresosMora": 0,
            "totalCobrado": 0,
            "totalCobradoAnterior": 0,
        },
        "meta_mensual": 0,
        "avance_meta": 0,
        "evolucion_mensual": [],
    }


@router.get("/financiamiento-tendencia-mensual")
def get_financiamiento_tendencia_mensual(
    fecha_inicio: Optional[str] = Query(None),
    meses: Optional[int] = Query(12),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
):
    """Tendencia mensual de financiamiento."""
    return {
        "meses": [],
    }


@router.get("/prestamos-por-concesionario")
def get_prestamos_por_concesionario(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
):
    """Préstamos por concesionario."""
    return {
        "concesionarios": [],
    }


@router.get("/prestamos-por-modelo")
def get_prestamos_por_modelo(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
):
    """Préstamos por modelo."""
    return {
        "modelos": [],
    }


@router.get("/financiamiento-por-rangos")
def get_financiamiento_por_rangos(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
):
    """Financiamiento por rangos."""
    return {
        "rangos": [],
        "total_prestamos": 0,
    }


@router.get("/composicion-morosidad")
def get_composicion_morosidad(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
):
    """Composición de morosidad."""
    return {
        "puntos": [],
        "total_morosidad": 0,
        "total_cuotas": 0,
    }


@router.get("/cobranza-fechas-especificas")
def get_cobranza_fechas_especificas(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
):
    """Cobranza por fechas específicas (mañana, hoy, 3 días atrás)."""
    return {
        "dias": [],
    }


@router.get("/cobranzas-semanales")
def get_cobranzas_semanales(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    semanas: Optional[int] = Query(12),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
):
    """Cobranzas semanales."""
    return {
        "semanas": [],
        "fecha_inicio": fecha_inicio or "",
        "fecha_fin": fecha_fin or "",
    }


@router.get("/morosidad-por-analista")
def get_morosidad_por_analista(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
):
    """Morosidad por analista."""
    return {
        "analistas": [],
    }


@router.get("/evolucion-morosidad")
def get_evolucion_morosidad(
    fecha_inicio: Optional[str] = Query(None),
    meses: Optional[int] = Query(12),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
):
    """Evolución de morosidad por mes."""
    return {
        "meses": [],
    }


@router.get("/evolucion-pagos")
def get_evolucion_pagos(
    fecha_inicio: Optional[str] = Query(None),
    meses: Optional[int] = Query(12),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
):
    """Evolución de pagos por mes."""
    return {
        "meses": [],
    }
