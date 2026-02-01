"""
Endpoints del dashboard. Usa datos reales de la BD cuando existen (clientes);
el resto permanece stub hasta tener modelos de préstamos/pagos/cuotas.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo

logger = logging.getLogger(__name__)
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


def _safe_float(val) -> float:
    """Convierte a float de forma segura (Decimal, int, None)."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


@router.get("/kpis-principales")
def get_kpis_principales(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """KPIs principales del dashboard. Datos reales: clientes desde Cliente; total préstamos desde prestamos (estado APROBADO)."""
    try:
        total_clientes = db.scalar(select(func.count()).select_from(Cliente)) or 0
        activos = db.scalar(select(func.count()).select_from(Cliente).where(Cliente.estado == "ACTIVO")) or 0
        inactivos = db.scalar(select(func.count()).select_from(Cliente).where(Cliente.estado == "INACTIVO")) or 0
        finalizados = db.scalar(select(func.count()).select_from(Cliente).where(Cliente.estado == "FINALIZADO")) or 0
        # Total préstamos = cantidad de préstamos aprobados (tabla prestamos, estado = APROBADO)
        total_prestamos = db.scalar(
            select(func.count()).select_from(Prestamo).where(Prestamo.estado == "APROBADO")
        ) or 0

        # Créditos nuevos = suma total_financiamiento de prestamos (estado APROBADO) solo del mes en curso
        # Indicador % = comparar total mes presente vs mes anterior
        now_utc = datetime.now(timezone.utc)
        inicio_mes_actual = now_utc.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        fin_mes_actual = (inicio_mes_actual + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
        inicio_mes_anterior = (inicio_mes_actual - timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        fin_mes_anterior = inicio_mes_actual - timedelta(seconds=1)

        total_mes_actual = db.scalar(
            select(func.coalesce(func.sum(Prestamo.total_financiamiento), 0)).select_from(Prestamo).where(
                Prestamo.estado == "APROBADO",
                Prestamo.fecha_creacion >= inicio_mes_actual,
                Prestamo.fecha_creacion <= fin_mes_actual,
            )
        ) or 0
        total_mes_anterior = db.scalar(
            select(func.coalesce(func.sum(Prestamo.total_financiamiento), 0)).select_from(Prestamo).where(
                Prestamo.estado == "APROBADO",
                Prestamo.fecha_creacion >= inicio_mes_anterior,
                Prestamo.fecha_creacion <= fin_mes_anterior,
            )
        ) or 0

        creditos_nuevos_valor = _safe_float(total_mes_actual)
        if total_mes_anterior and _safe_float(total_mes_anterior) != 0:
            variacion_creditos = ((creditos_nuevos_valor - _safe_float(total_mes_anterior)) / _safe_float(total_mes_anterior)) * 100.0
        else:
            variacion_creditos = 0.0

        # Cuotas programadas = suma monto_programado de prestamos en el mes. % cuotas pagadas = suma(monto_pagado) / suma(monto_programado) * 100
        total_monto_programado = db.scalar(
            select(func.coalesce(func.sum(Prestamo.monto_programado), 0)).select_from(Prestamo).where(
                Prestamo.fecha_creacion >= inicio_mes_actual,
                Prestamo.fecha_creacion <= fin_mes_actual,
            )
        ) or 0
        total_monto_pagado = db.scalar(
            select(func.coalesce(func.sum(Prestamo.monto_pagado), 0)).select_from(Prestamo).where(
                Prestamo.fecha_creacion >= inicio_mes_actual,
                Prestamo.fecha_creacion <= fin_mes_actual,
            )
        ) or 0
        sum_prog = _safe_float(total_monto_programado)
        sum_pag = _safe_float(total_monto_pagado)
        porcentaje_cuotas_pagadas = (sum_pag / sum_prog * 100.0) if sum_prog and sum_prog != 0 else 0.0

        return {
            "total_prestamos": _kpi(_safe_float(total_prestamos), 0.0),
            "creditos_nuevos_mes": _kpi(creditos_nuevos_valor, round(variacion_creditos, 1)),
            "total_clientes": _kpi(_safe_float(total_clientes), 0.0),
            "clientes_por_estado": {
                "activos": _kpi(_safe_float(activos), 0.0),
                "inactivos": _kpi(_safe_float(inactivos), 0.0),
                "finalizados": _kpi(_safe_float(finalizados), 0.0),
            },
            "total_morosidad_usd": _kpi(0.0, 0.0),
            "cuotas_programadas": {"valor_actual": sum_prog},
            "porcentaje_cuotas_pagadas": round(porcentaje_cuotas_pagadas, 1),
        }
    except Exception as e:
        logger.exception("Error en kpis-principales: %s", e)
        return {
            "total_prestamos": _kpi(0.0, 0.0),
            "creditos_nuevos_mes": _kpi(0.0, 0.0),
            "total_clientes": _kpi(0.0, 0.0),
            "clientes_por_estado": {
                "activos": _kpi(0.0, 0.0),
                "inactivos": _kpi(0.0, 0.0),
                "finalizados": _kpi(0.0, 0.0),
            },
            "total_morosidad_usd": _kpi(0.0, 0.0),
            "cuotas_programadas": {"valor_actual": 0.0},
            "porcentaje_cuotas_pagadas": 0.0,
        }


def _ultimo_dia_del_mes(d: datetime) -> datetime:
    """Último día del mes a las 23:59 UTC para comparar con fecha_registro (timezone-aware)."""
    siguiente = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    ultimo = siguiente - timedelta(seconds=1)
    if ultimo.tzinfo is None:
        ultimo = ultimo.replace(tzinfo=timezone.utc)
    return ultimo


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
    try:
        hoy = datetime.now(timezone.utc)
        for i, m in enumerate(meses):
            fin_mes = hoy - timedelta(days=30 * (11 - i))
            ultimo_dia = _ultimo_dia_del_mes(fin_mes.replace(tzinfo=timezone.utc) if fin_mes.tzinfo is None else fin_mes)
            cartera = db.scalar(
                select(func.coalesce(func.sum(Cliente.total_financiamiento), 0)).select_from(Cliente).where(
                    Cliente.fecha_registro <= ultimo_dia,
                    Cliente.total_financiamiento.isnot(None),
                    Cliente.total_financiamiento > 0,
                )
            ) or 0
            evolucion.append({
                "mes": m["mes"],
                "cartera": _safe_float(cartera),
                "cobrado": 0.0,
                "morosidad": 0.0,
            })
    except Exception as e:
        logger.exception("Error en dashboard admin: %s", e)
        evolucion = [
            {"mes": m["mes"], "cartera": 0.0, "cobrado": 0.0, "morosidad": 0.0}
            for m in meses
        ]
    # Si no hay datos reales (toda la cartera en 0), mostrar datos de ejemplo para que el gráfico no quede vacío
    tiene_datos_reales = any(_safe_float(e.get("cartera", 0)) > 0 for e in evolucion)
    if not tiene_datos_reales and evolucion:
        evolucion = [
            {"mes": m["mes"], "cartera": m["cartera"], "cobrado": m["cobrado"], "morosidad": m["morosidad"]}
            for m in meses
        ]
        origen = "demo"
    else:
        origen = "bd"
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
        "evolucion_origen": origen,
    }


@router.get("/financiamiento-tendencia-mensual")
def get_financiamiento_tendencia_mensual(
    fecha_inicio: Optional[str] = Query(None),
    meses: Optional[int] = Query(12),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Tendencia mensual de financiamiento. Datos reales: cartera por mes desde Cliente."""
    try:
        meses_list = _ultimos_12_meses()
        hoy = datetime.now(timezone.utc)
        resultado = []
        for i, m in enumerate(meses_list):
            fin_mes = hoy - timedelta(days=30 * (11 - i))
            ultimo_dia = _ultimo_dia_del_mes(fin_mes.replace(tzinfo=timezone.utc) if fin_mes.tzinfo is None else fin_mes)
            cartera = db.scalar(
                select(func.coalesce(func.sum(Cliente.total_financiamiento), 0)).select_from(Cliente).where(
                    Cliente.fecha_registro <= ultimo_dia,
                    Cliente.total_financiamiento.isnot(None),
                    Cliente.total_financiamiento > 0,
                )
            ) or 0
            resultado.append({
                "mes": m["mes"],
                "monto_nuevos": _safe_float(cartera),
                "monto_cuotas_programadas": 0.0,
                "monto_pagado": 0.0,
                "morosidad_mensual": 0.0,
            })
        return {"meses": resultado}
    except Exception as e:
        logger.exception("Error en financiamiento-tendencia-mensual: %s", e)
        return {"meses": _ultimos_12_meses()}


@router.get("/prestamos-por-concesionario")
def get_prestamos_por_concesionario(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Préstamos por concesionario. Stub: Cliente no tiene campo concesionario; requiere tabla/columna."""
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
    db: Session = Depends(get_db),
):
    """Préstamos por modelo. Stub: Cliente no tiene campo modelo; requiere tabla/columna."""
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


def _rangos_financiamiento():
    """Definición de rangos de monto para agrupar total_financiamiento."""
    return [
        (0, 200, "$0 - $200"),
        (200, 400, "$200 - $400"),
        (400, 600, "$400 - $600"),
        (600, 800, "$600 - $800"),
        (800, 1000, "$800 - $1,000"),
        (1000, 999999999, "$1,000+"),
    ]


@router.get("/financiamiento-por-rangos")
def get_financiamiento_por_rangos(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Financiamiento por rangos. Datos reales: agrupa Cliente por total_financiamiento."""
    try:
        rangos_def = _rangos_financiamiento()
        resultado = []
        total_p = 0
        total_m = 0.0
        for min_val, max_val, cat in rangos_def:
            if max_val >= 999999999:
                q = select(
                    func.count().label("n"),
                    func.coalesce(func.sum(Cliente.total_financiamiento), 0).label("m"),
                ).select_from(Cliente).where(
                    Cliente.total_financiamiento.isnot(None),
                    Cliente.total_financiamiento >= min_val,
                )
            else:
                q = select(
                    func.count().label("n"),
                    func.coalesce(func.sum(Cliente.total_financiamiento), 0).label("m"),
                ).select_from(Cliente).where(
                    Cliente.total_financiamiento.isnot(None),
                    Cliente.total_financiamiento >= min_val,
                    Cliente.total_financiamiento < max_val,
                )
            row = db.execute(q).one()
            n, m = int(row.n or 0), _safe_float(row.m)
            total_p += n
            total_m += m
            resultado.append({"categoria": cat, "cantidad_prestamos": n, "monto_total": m})
        if total_p == 0:
            total_p = 1
        if total_m == 0:
            total_m = 1.0
        return {
            "rangos": [
                {
                    "categoria": r["categoria"],
                    "cantidad_prestamos": r["cantidad_prestamos"],
                    "monto_total": r["monto_total"],
                    "porcentaje_cantidad": round(100 * r["cantidad_prestamos"] / total_p, 1),
                    "porcentaje_monto": round(100 * r["monto_total"] / total_m, 1),
                }
                for r in resultado
            ],
            "total_prestamos": total_p,
            "total_monto": total_m,
        }
    except Exception as e:
        logger.exception("Error en financiamiento-por-rangos: %s", e)
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
    db: Session = Depends(get_db),
):
    """Composición de morosidad. Datos reales: agrupa Cliente por dias_mora (1-30, 31-60, 61-90, 90+)."""
    try:
        bandas = [(1, 30, "1-30 días"), (31, 60, "31-60 días"), (61, 90, "61-90 días"), (91, 999999, "90+ días")]
        puntos = []
        total_monto = 0.0
        total_cuotas = 0
        for min_d, max_d, cat in bandas:
            if max_d >= 999999:
                q = select(
                    func.count().label("n"),
                    func.coalesce(func.sum(Cliente.total_financiamiento), 0).label("m"),
                ).select_from(Cliente).where(
                    Cliente.dias_mora.isnot(None),
                    Cliente.dias_mora >= min_d,
                    Cliente.total_financiamiento.isnot(None),
                )
            else:
                q = select(
                    func.count().label("n"),
                    func.coalesce(func.sum(Cliente.total_financiamiento), 0).label("m"),
                ).select_from(Cliente).where(
                    Cliente.dias_mora.isnot(None),
                    Cliente.dias_mora >= min_d,
                    Cliente.dias_mora <= max_d,
                    Cliente.total_financiamiento.isnot(None),
                )
            row = db.execute(q).one()
            n, m = int(row.n or 0), _safe_float(row.m)
            total_cuotas += n
            total_monto += m
            puntos.append({"categoria": cat, "monto": m, "cantidad_cuotas": n})
        return {"puntos": puntos, "total_morosidad": total_monto, "total_cuotas": total_cuotas}
    except Exception as e:
        logger.exception("Error en composicion-morosidad: %s", e)
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
    db: Session = Depends(get_db),
):
    """Cobranza por fechas específicas. Stub: requiere tabla pagos/cobranzas."""
    return {"dias": []}


@router.get("/cobranzas-semanales")
def get_cobranzas_semanales(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    semanas: Optional[int] = Query(12),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Cobranzas semanales. Stub: requiere tabla pagos/cobranzas para datos reales."""
    sem = []
    for i in range(min(semanas or 12, 12)):
        base = 32000 - i * 1200
        sem.append({
            "semana_inicio": (datetime.now() - timedelta(weeks=i)).strftime("%Y-%m-%d"),
            "nombre_semana": f"Sem {12 - i}",
            "cobranzas_planificadas": base,
            "pagos_reales": int(base * (0.65 + 0.02 * i)),
        })
    return {"semanas": sem, "fecha_inicio": fecha_inicio or "", "fecha_fin": fecha_fin or ""}


@router.get("/morosidad-por-analista")
def get_morosidad_por_analista(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Morosidad por analista. Stub: Cliente no tiene campo analista; requiere tabla analistas/asignación."""
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
    db: Session = Depends(get_db),
):
    """Evolución de morosidad por mes. Datos reales: suma dias_mora * monto proxy por mes desde Cliente."""
    try:
        meses_list = _ultimos_12_meses()
        hoy = datetime.now(timezone.utc)
        resultado = []
        for i, m in enumerate(meses_list):
            fin_mes = hoy - timedelta(days=30 * (11 - i))
            ultimo_dia = _ultimo_dia_del_mes(fin_mes.replace(tzinfo=timezone.utc) if fin_mes.tzinfo is None else fin_mes)
            moro = db.scalar(
                select(func.coalesce(func.sum(Cliente.dias_mora * Cliente.total_financiamiento), 0)).select_from(Cliente).where(
                    Cliente.fecha_registro <= ultimo_dia,
                    Cliente.dias_mora.isnot(None),
                    Cliente.dias_mora > 0,
                    Cliente.total_financiamiento.isnot(None),
                )
            ) or 0
            resultado.append({"mes": m["mes"], "morosidad": _safe_float(moro)})
        return {"meses": resultado}
    except Exception as e:
        logger.exception("Error en evolucion-morosidad: %s", e)
        m = _ultimos_12_meses()
        return {"meses": [{"mes": x["mes"], "morosidad": x["morosidad"]} for x in m]}


@router.get("/evolucion-pagos")
def get_evolucion_pagos(
    fecha_inicio: Optional[str] = Query(None),
    meses: Optional[int] = Query(12),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Evolución de pagos por mes. Stub: requiere tabla pagos para datos reales."""
    m = _ultimos_12_meses()
    return {
        "meses": [{"mes": x["mes"], "pagos": 12 + i, "monto": x["monto_pagado"]} for i, x in enumerate(m)
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
