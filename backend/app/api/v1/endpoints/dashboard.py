"""
Endpoints del dashboard. Usa datos reales de la BD cuando existen (clientes);
el resto permanece stub hasta tener modelos de préstamos/pagos/cuotas.
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.cliente import Cliente

router = APIRouter()


def _kpi(valor: float = 0, variacion: float = 0) -> dict:
    return {"valor_actual": valor, "variacion_porcentual": variacion}


def _ultimos_12_meses() -> list[dict]:
    """Genera los últimos 12 meses con datos demo para gráficos."""
    meses = []
    hoy = datetime.now()
    nombres = ("Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic")
    for i in range(11, -1, -1):
        d = hoy - timedelta(days=30 * i)
        mes = d.month
        año = d.year
        label = f"{nombres[mes - 1]} {año}"
        # Valores demo crecientes para que se vean las series
        base = 50_000 + (11 - i) * 8_000
        meses.append({
            "mes": label,
            "cartera": base + (i * 2_000),
            "cobrado": int(base * 0.6) + (i * 1_500),
            "morosidad": int(base * 0.08) + (i * 200),
            "cantidad_nuevos": 15 + i,
            "monto_nuevos": base,
            "total_acumulado": base * (12 - i),
            "monto_cuotas_programadas": int(base * 0.7),
            "monto_pagado": int(base * 0.55),
            "morosidad_mensual": int(base * 0.07),
        })
    return meses


@router.get("/opciones-filtros")
def get_opciones_filtros(db: Session = Depends(get_db)):
    """Opciones para filtros: analistas, concesionarios, modelos. Desde BD cuando existan campos."""
    # Cliente no tiene analista/concesionario/modelo; dejar listas vacías hasta tener esos campos
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
    db: Session = Depends(get_db),
):
    """KPIs principales del dashboard. Datos reales: clientes y conteos desde BD."""
    total_clientes = db.scalar(select(func.count()).select_from(Cliente)) or 0
    activos = db.scalar(select(func.count()).select_from(Cliente).where(Cliente.estado == "ACTIVO")) or 0
    inactivos = db.scalar(select(func.count()).select_from(Cliente).where(Cliente.estado == "INACTIVO")) or 0
    finalizados = db.scalar(select(func.count()).select_from(Cliente).where(Cliente.estado == "FINALIZADO")) or 0
    # Préstamos: clientes con financiamiento registrado
    total_prestamos = db.scalar(
        select(func.count()).select_from(Cliente).where(Cliente.total_financiamiento.isnot(None), Cliente.total_financiamiento > 0)
    ) or 0
    # Créditos nuevos mes: registros este mes (fecha_registro)
    inicio_mes = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    creditos_nuevos_mes = db.scalar(
        select(func.count()).select_from(Cliente).where(Cliente.fecha_registro >= inicio_mes)
    ) or 0
    # Morosidad/cuotas: sin tabla pagos/cuotas se deja en 0
    return {
        "total_prestamos": _kpi(float(total_prestamos), 0.0),
        "creditos_nuevos_mes": _kpi(float(creditos_nuevos_mes), 0.0),
        "total_clientes": _kpi(float(total_clientes), 0.0),
        "clientes_por_estado": {
            "activos": _kpi(float(activos), 0.0),
            "inactivos": _kpi(float(inactivos), 0.0),
            "finalizados": _kpi(float(finalizados), 0.0),
        },
        "total_morosidad_usd": _kpi(0.0, 0.0),
        "cuotas_programadas": {"valor_actual": 0.0},
        "porcentaje_cuotas_pagadas": 0.0,
    }


def _ultimo_dia_del_mes(d: datetime) -> datetime:
    """Último día del mes a las 23:59 para comparar con fecha_registro."""
    siguiente = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    return siguiente - timedelta(seconds=1)


@router.get("/admin")
def get_dashboard_admin(
    periodo: Optional[str] = Query(None),
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Dashboard admin: evolucion_mensual con datos reales (cartera desde Cliente); financieros/meta stub."""
    meses = _ultimos_12_meses()
    evolucion = []
    hoy = datetime.now()
    for i, m in enumerate(meses):
        fin_mes = hoy - timedelta(days=30 * (11 - i))
        ultimo_dia = _ultimo_dia_del_mes(fin_mes)
        cartera = db.scalar(
            select(func.coalesce(func.sum(Cliente.total_financiamiento), 0)).select_from(Cliente).where(
                Cliente.fecha_registro <= ultimo_dia,
                Cliente.total_financiamiento.isnot(None),
                Cliente.total_financiamiento > 0,
            )
        ) or 0
        evolucion.append({
            "mes": m["mes"],
            "cartera": float(cartera),
            "cobrado": 0.0,
            "morosidad": 0.0,
        })
    return {
        "financieros": {
            "ingresosCapital": 0.0,
            "ingresosInteres": 0.0,
            "ingresosMora": 0.0,
            "totalCobrado": 0.0,
            "totalCobradoAnterior": 0.0,
        },
        "meta_mensual": 0.0,
        "avance_meta": 0.0,
        "evolucion_mensual": evolucion,
    }


@router.get("/financiamiento-tendencia-mensual")
def get_financiamiento_tendencia_mensual(
    fecha_inicio: Optional[str] = Query(None),
    meses: Optional[int] = Query(12),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
):
    """Tendencia mensual de financiamiento (datos demo)."""
    return {"meses": _ultimos_12_meses()}


@router.get("/prestamos-por-concesionario")
def get_prestamos_por_concesionario(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
):
    """Préstamos por concesionario (datos demo)."""
    datos = [
        ("Concesionario A", 420, 33.7),
        ("Concesionario B", 318, 25.5),
        ("Concesionario C", 245, 19.6),
        ("Concesionario D", 164, 13.2),
        ("Concesionario E", 100, 8.0),
    ]
    return {
        "concesionarios": [{"concesionario": n, "total_prestamos": int(c * 1200), "cantidad_prestamos": c, "porcentaje": p} for n, c, p in datos],
    }


@router.get("/prestamos-por-modelo")
def get_prestamos_por_modelo(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
):
    """Préstamos por modelo (datos demo)."""
    datos = [
        ("Modelo X", 380, 30.5),
        ("Modelo Y", 295, 23.6),
        ("Modelo Z", 220, 17.6),
        ("Modelo W", 182, 14.6),
        ("Otros", 170, 13.6),
    ]
    return {
        "modelos": [{"modelo": n, "total_prestamos": int(c * 1500), "cantidad_prestamos": c, "porcentaje": p} for n, c, p in datos],
    }


@router.get("/financiamiento-por-rangos")
def get_financiamiento_por_rangos(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
):
    """Financiamiento por rangos (datos demo)."""
    rangos = [
        ("$0 - $200", 85, 12000),
        ("$200 - $400", 120, 36000),
        ("$400 - $600", 95, 47500),
        ("$600 - $800", 70, 49000),
        ("$800 - $1,000", 45, 40500),
        ("$1,000+", 32, 55000),
    ]
    total_p = sum(r[1] for r in rangos)
    total_m = sum(r[2] for r in rangos)
    return {
        "rangos": [
            {"categoria": c, "cantidad_prestamos": n, "monto_total": m, "porcentaje_cantidad": round(100 * n / total_p, 1), "porcentaje_monto": round(100 * m / total_m, 1)}
            for c, n, m in rangos
        ],
        "total_prestamos": total_p,
        "total_monto": float(total_m),
    }


@router.get("/composicion-morosidad")
def get_composicion_morosidad(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
):
    """Composición de morosidad (datos demo)."""
    puntos = [
        ("1-30 días", 12000, 45),
        ("31-60 días", 8500, 28),
        ("61-90 días", 6200, 18),
        ("90+ días", 15800, 32),
    ]
    return {
        "puntos": [{"categoria": c, "monto": m, "cantidad_cuotas": n} for c, m, n in puntos],
        "total_morosidad": sum(p[1] for p in puntos),
        "total_cuotas": sum(p[2] for p in puntos),
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
    """Cobranzas semanales (datos demo)."""
    sem = []
    for i in range(min(semanas or 12, 12)):
        base = 32000 - i * 1200
        sem.append({
            "semana_inicio": (datetime.now() - timedelta(weeks=i)).strftime("%Y-%m-%d"),
            "nombre_semana": f"Sem {12 - i}",
            "cobranzas_planificadas": base,
            "pagos_reales": int(base * (0.65 + 0.02 * i)),
        })
    return {
        "semanas": sem,
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
    """Morosidad por analista (datos demo)."""
    return {
        "analistas": [
            {"analista": "Analista 1", "total_morosidad": 15200, "cantidad_clientes": 45},
            {"analista": "Analista 2", "total_morosidad": 11800, "cantidad_clientes": 38},
            {"analista": "Analista 3", "total_morosidad": 9500, "cantidad_clientes": 32},
            {"analista": "Analista 4", "total_morosidad": 6000, "cantidad_clientes": 22},
        ],
    }


@router.get("/evolucion-morosidad")
def get_evolucion_morosidad(
    fecha_inicio: Optional[str] = Query(None),
    meses: Optional[int] = Query(12),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
):
    """Evolución de morosidad por mes (datos demo)."""
    m = _ultimos_12_meses()
    return {"meses": [{"mes": x["mes"], "morosidad": x["morosidad"]} for x in m]}


@router.get("/evolucion-pagos")
def get_evolucion_pagos(
    fecha_inicio: Optional[str] = Query(None),
    meses: Optional[int] = Query(12),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
):
    """Evolución de pagos por mes (datos demo). Frontend espera mes, pagos (cantidad), monto."""
    m = _ultimos_12_meses()
    return {
        "meses": [
            {"mes": x["mes"], "pagos": 12 + i, "monto": x["monto_pagado"]}
            for i, x in enumerate(m)
        ]
    }


# ========== Endpoints adicionales usados por modales/páginas (stub) ==========

@router.get("/cobranza-por-dia")
def get_cobranza_por_dia(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
):
    """Cobranza por día (DashboardCobranza, CobranzaPorDiaModal, CobranzaPlanificadaRealModal)."""
    return {"dias": []}


@router.get("/cobranzas-mensuales")
def get_cobranzas_mensuales(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
):
    """Cobranzas mensuales (CobranzasMensualesModal)."""
    return {"meses": []}


@router.get("/cobros-por-analista")
def get_cobros_por_analista(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
):
    """Cobros por analista (DashboardCobranza)."""
    return {"analistas": []}


@router.get("/cobros-diarios")
def get_cobros_diarios(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
):
    """Cobros diarios (DashboardAnalisis)."""
    return {"dias": []}


@router.get("/cuentas-cobrar-tendencias")
def get_cuentas_cobrar_tendencias(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
):
    """Tendencias cuentas por cobrar (TendenciasModal)."""
    return {"tendencias": []}


@router.get("/distribucion-prestamos")
def get_distribucion_prestamos(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
):
    """Distribución de préstamos (BarrasDivergentesModal)."""
    return {"distribucion": []}


@router.get("/metricas-acumuladas")
def get_metricas_acumuladas(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
):
    """Métricas acumuladas (CobranzaPorDiaModal)."""
    return {"metricas": []}
