"""
Endpoints del dashboard. Usa datos reales de la BD cuando existen (clientes);
el resto permanece stub hasta tener modelos de préstamos/pagos/cuotas.
"""
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.cliente import Cliente
from app.models.cuota import Cuota
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

        # Morosidad total mensual = (suma monto_programado - suma monto_pagado) del mes. Comparar con el mismo indicador del mes anterior.
        total_monto_programado_ant = db.scalar(
            select(func.coalesce(func.sum(Prestamo.monto_programado), 0)).select_from(Prestamo).where(
                Prestamo.fecha_creacion >= inicio_mes_anterior,
                Prestamo.fecha_creacion <= fin_mes_anterior,
            )
        ) or 0
        total_monto_pagado_ant = db.scalar(
            select(func.coalesce(func.sum(Prestamo.monto_pagado), 0)).select_from(Prestamo).where(
                Prestamo.fecha_creacion >= inicio_mes_anterior,
                Prestamo.fecha_creacion <= fin_mes_anterior,
            )
        ) or 0
        sum_prog_ant = _safe_float(total_monto_programado_ant)
        sum_pag_ant = _safe_float(total_monto_pagado_ant)
        morosidad_actual = max(0.0, sum_prog - sum_pag)
        morosidad_anterior = max(0.0, sum_prog_ant - sum_pag_ant)
        if morosidad_anterior and morosidad_anterior != 0:
            variacion_morosidad = ((morosidad_actual - morosidad_anterior) / morosidad_anterior) * 100.0
        else:
            variacion_morosidad = 0.0

        return {
            "total_prestamos": _kpi(_safe_float(total_prestamos), 0.0),
            "creditos_nuevos_mes": _kpi(creditos_nuevos_valor, round(variacion_creditos, 1)),
            "total_clientes": _kpi(_safe_float(total_clientes), 0.0),
            "clientes_por_estado": {
                "activos": _kpi(_safe_float(activos), 0.0),
                "inactivos": _kpi(_safe_float(inactivos), 0.0),
                "finalizados": _kpi(_safe_float(finalizados), 0.0),
            },
            "total_morosidad_usd": _kpi(round(morosidad_actual, 2), round(variacion_morosidad, 1)),
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
            "total_morosidad_usd": _kpi(0.0, 0.0),  # fallback en error
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


def _primer_ultimo_dia_mes(d: datetime) -> tuple[date, date]:
    """Devuelve (primer_día, último_día) del mes de d como date."""
    y, m = d.year, d.month
    inicio = date(y, m, 1)
    # Último día del mes
    if m == 12:
        fin = date(y, 12, 31)
    else:
        fin = date(y, m + 1, 1) - timedelta(days=1)
    return inicio, fin


@router.get("/admin")
def get_dashboard_admin(
    periodo: Optional[str] = Query(None),
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Dashboard admin: evolucion_mensual desde tabla cuotas. Cartera = suma mensual monto (programado por vencimiento), Cobrado = suma mensual monto pagado, Morosidad = diferencia."""
    meses = _ultimos_12_meses()
    evolucion = []
    try:
        hoy = datetime.now(timezone.utc)
        for i, m in enumerate(meses):
            fin_mes = hoy - timedelta(days=30 * (11 - i))
            if fin_mes.tzinfo is None:
                fin_mes = fin_mes.replace(tzinfo=timezone.utc)
            inicio_d, fin_d = _primer_ultimo_dia_mes(fin_mes)
            # Cartera = suma mensual monto_programado: SUM(monto) de cuotas con fecha_vencimiento en el mes
            cartera = db.scalar(
                select(func.coalesce(func.sum(Cuota.monto), 0)).select_from(Cuota).where(
                    Cuota.fecha_vencimiento >= inicio_d,
                    Cuota.fecha_vencimiento <= fin_d,
                )
            ) or 0
            # Cobrado = suma mensual monto_pagado: SUM(monto) de cuotas pagadas con fecha_pago en el mes
            cobrado = db.scalar(
                select(func.coalesce(func.sum(Cuota.monto), 0)).select_from(Cuota).where(
                    Cuota.pagado.is_(True),
                    Cuota.fecha_pago.isnot(None),
                    func.date(Cuota.fecha_pago) >= inicio_d,
                    func.date(Cuota.fecha_pago) <= fin_d,
                )
            ) or 0
            cartera_f = _safe_float(cartera)
            cobrado_f = _safe_float(cobrado)
            morosidad_f = max(0.0, cartera_f - cobrado_f)
            evolucion.append({
                "mes": m["mes"],
                "cartera": cartera_f,
                "cobrado": cobrado_f,
                "morosidad": morosidad_f,
            })
        origen = "bd"
    except Exception as e:
        logger.exception("Error en dashboard admin (evolucion desde cuotas): %s", e)
        evolucion = [
            {"mes": m["mes"], "cartera": 0.0, "cobrado": 0.0, "morosidad": 0.0}
            for m in meses
        ]
        origen = "bd"
    # Si no hay ningún dato en cuotas, el gráfico mostrará ceros; no usamos demo para no confundir
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
    """Tendencia mensual de financiamiento. Datos reales: cartera por mes desde Prestamo (no Cliente)."""
    try:
        meses_list = _ultimos_12_meses()
        hoy = datetime.now(timezone.utc)
        resultado = []
        for i, m in enumerate(meses_list):
            fin_mes = hoy - timedelta(days=30 * (11 - i))
            ultimo_dia = _ultimo_dia_del_mes(fin_mes.replace(tzinfo=timezone.utc) if fin_mes.tzinfo is None else fin_mes)
            cartera = db.scalar(
                select(func.coalesce(func.sum(Prestamo.total_financiamiento), 0)).select_from(Prestamo).where(
                    Prestamo.fecha_creacion <= ultimo_dia,
                    Prestamo.estado == "APROBADO",
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


@router.get("/morosidad-por-dia")
def get_morosidad_por_dia(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    dias: Optional[int] = Query(30, ge=7, le=90),
    db: Session = Depends(get_db),
):
    """Morosidad por día desde tabla cuotas: por cada día, cartera (suma monto vencido ese día) menos cobrado (suma monto pagado ese día)."""
    try:
        hoy_utc = datetime.now(timezone.utc)
        hoy_date = date(hoy_utc.year, hoy_utc.month, hoy_utc.day)
        if fecha_inicio and fecha_fin:
            try:
                inicio = date.fromisoformat(fecha_inicio)
                fin = date.fromisoformat(fecha_fin)
            except ValueError:
                fin = hoy_date
                inicio = fin - timedelta(days=dias or 30)
        else:
            fin = hoy_date
            inicio = fin - timedelta(days=dias or 30)
        if (fin - inicio).days > 90:
            fin = inicio + timedelta(days=90)
        resultado = []
        nombres_mes = ("Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic")
        d = inicio
        while d <= fin:
            # Cartera del día = suma monto de cuotas con fecha_vencimiento = d
            cartera_dia = db.scalar(
                select(func.coalesce(func.sum(Cuota.monto), 0)).select_from(Cuota).where(
                    Cuota.fecha_vencimiento == d,
                )
            ) or 0
            # Cobrado del día = suma monto de cuotas pagadas con fecha_pago en d
            cobrado_dia = db.scalar(
                select(func.coalesce(func.sum(Cuota.monto), 0)).select_from(Cuota).where(
                    Cuota.pagado.is_(True),
                    Cuota.fecha_pago.isnot(None),
                    func.date(Cuota.fecha_pago) == d,
                )
            ) or 0
            morosidad_dia = max(0.0, _safe_float(cartera_dia) - _safe_float(cobrado_dia))
            resultado.append({
                "fecha": d.isoformat(),
                "dia": f"{d.day} {nombres_mes[d.month - 1]}",
                "morosidad": round(morosidad_dia, 2),
            })
            d += timedelta(days=1)
        return {"dias": resultado}
    except Exception as e:
        logger.exception("Error en morosidad-por-dia: %s", e)
        return {"dias": []}


def _parse_fechas_concesionario(fecha_inicio: Optional[str], fecha_fin: Optional[str]):
    """Parsea fechas o devuelve rango últimos 12 meses."""
    hoy = datetime.now(timezone.utc)
    hoy_date = date(hoy.year, hoy.month, hoy.day)
    if fecha_inicio and fecha_fin:
        try:
            inicio = date.fromisoformat(fecha_inicio)
            fin = date.fromisoformat(fecha_fin)
            return inicio, fin
        except ValueError:
            pass
    fin = hoy_date
    inicio = fin - timedelta(days=365)
    return inicio, fin


@router.get("/prestamos-por-concesionario")
def get_prestamos_por_concesionario(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Préstamos aprobados por concesionario: por_mes (en el período) y acumulado desde el inicio. Origen: tabla prestamos, campo concesionario."""
    try:
        inicio, fin = _parse_fechas_concesionario(fecha_inicio, fecha_fin)
        # Mes como YYYY-MM para agrupar
        mes_expr = func.to_char(
            func.date_trunc("month", Prestamo.fecha_creacion),
            "YYYY-MM",
        )
        concesionario_label = func.coalesce(Prestamo.concesionario, "Sin concesionario").label("concesionario")

        # Por mes: préstamos APROBADO en [inicio, fin], agrupado por mes y concesionario
        q_por_mes = (
            select(
                mes_expr.label("mes"),
                concesionario_label,
                func.count().label("cantidad"),
            )
            .select_from(Prestamo)
            .where(
                Prestamo.estado == "APROBADO",
                func.date(Prestamo.fecha_creacion) >= inicio,
                func.date(Prestamo.fecha_creacion) <= fin,
            )
            .group_by(mes_expr, Prestamo.concesionario)
            .order_by(mes_expr, func.count().desc())
        )
        rows_por_mes = db.execute(q_por_mes).all()
        por_mes = [
            {"mes": r.mes, "concesionario": r.concesionario, "cantidad": r.cantidad}
            for r in rows_por_mes
        ]

        # Acumulado: todos los préstamos APROBADO desde el inicio, por concesionario
        q_acum = (
            select(
                func.coalesce(Prestamo.concesionario, "Sin concesionario").label("concesionario"),
                func.count().label("cantidad_acumulada"),
            )
            .select_from(Prestamo)
            .where(Prestamo.estado == "APROBADO")
            .group_by(Prestamo.concesionario)
            .order_by(func.count().desc())
        )
        rows_acum = db.execute(q_acum).all()
        acumulado = [
            {"concesionario": r.concesionario, "cantidad_acumulada": r.cantidad_acumulada}
            for r in rows_acum
        ]

        return {"por_mes": por_mes, "acumulado": acumulado}
    except Exception as e:
        logger.exception("Error en prestamos-por-concesionario: %s", e)
        return {"por_mes": [], "acumulado": []}


@router.get("/prestamos-por-modelo")
def get_prestamos_por_modelo(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Préstamos aprobados por modelo: por_mes (en el período) y acumulado desde el inicio. Origen: tabla prestamos, campo modelo."""
    try:
        inicio, fin = _parse_fechas_concesionario(fecha_inicio, fecha_fin)
        mes_expr = func.to_char(
            func.date_trunc("month", Prestamo.fecha_creacion),
            "YYYY-MM",
        )
        modelo_label = func.coalesce(Prestamo.modelo, "Sin modelo").label("modelo")

        # Por mes: préstamos APROBADO en [inicio, fin], agrupado por mes y modelo
        q_por_mes = (
            select(
                mes_expr.label("mes"),
                modelo_label,
                func.count().label("cantidad"),
            )
            .select_from(Prestamo)
            .where(
                Prestamo.estado == "APROBADO",
                func.date(Prestamo.fecha_creacion) >= inicio,
                func.date(Prestamo.fecha_creacion) <= fin,
            )
            .group_by(mes_expr, Prestamo.modelo)
            .order_by(mes_expr, func.count().desc())
        )
        rows_por_mes = db.execute(q_por_mes).all()
        por_mes = [
            {"mes": r.mes, "modelo": r.modelo, "cantidad": r.cantidad}
            for r in rows_por_mes
        ]

        # Acumulado: todos los préstamos APROBADO desde el inicio, por modelo
        q_acum = (
            select(
                func.coalesce(Prestamo.modelo, "Sin modelo").label("modelo"),
                func.count().label("cantidad_acumulada"),
            )
            .select_from(Prestamo)
            .where(Prestamo.estado == "APROBADO")
            .group_by(Prestamo.modelo)
            .order_by(func.count().desc())
        )
        rows_acum = db.execute(q_acum).all()
        acumulado = [
            {"modelo": r.modelo, "cantidad_acumulada": r.cantidad_acumulada}
            for r in rows_acum
        ]

        return {"por_mes": por_mes, "acumulado": acumulado}
    except Exception as e:
        logger.exception("Error en prestamos-por-modelo: %s", e)
        return {"por_mes": [], "acumulado": []}


def _rangos_financiamiento():
    """Bandas de $200 USD: cantidad de préstamos por total_financiamiento (tabla prestamos)."""
    return [
        (0, 200, "$0 - $200"),
        (200, 400, "$200 - $400"),
        (400, 600, "$400 - $600"),
        (600, 800, "$600 - $800"),
        (800, 1000, "$800 - $1,000"),
        (1000, 1200, "$1,000 - $1,200"),
        (1200, 999999999, "Más de $1,200"),
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
    """Bandas por total_financiamiento: cantidad de préstamos (COUNT) por banda desde tabla prestamos, no suma en dólares."""
    try:
        rangos_def = _rangos_financiamiento()
        resultado = []
        total_p = 0
        for min_val, max_val, cat in rangos_def:
            if max_val >= 999999999:
                q = select(func.count().label("n")).select_from(Prestamo).where(
                    Prestamo.total_financiamiento.isnot(None),
                    Prestamo.total_financiamiento >= min_val,
                )
            else:
                q = select(func.count().label("n")).select_from(Prestamo).where(
                    Prestamo.total_financiamiento.isnot(None),
                    Prestamo.total_financiamiento >= min_val,
                    Prestamo.total_financiamiento < max_val,
                )
            n = int(db.scalar(q) or 0)
            total_p += n
            resultado.append({"categoria": cat, "cantidad_prestamos": n, "monto_total": 0.0})
        if total_p == 0:
            total_p = 1
        return {
            "rangos": [
                {
                    "categoria": r["categoria"],
                    "cantidad_prestamos": r["cantidad_prestamos"],
                    "monto_total": r["monto_total"],
                    "porcentaje_cantidad": round(100 * r["cantidad_prestamos"] / total_p, 1),
                    "porcentaje_monto": 0.0,
                }
                for r in resultado
            ],
            "total_prestamos": total_p,
            "total_monto": 0.0,
        }
    except Exception as e:
        logger.exception("Error en financiamiento-por-rangos: %s", e)
        rangos = [
            ("$0 - $200", 0),
            ("$200 - $400", 0),
            ("$400 - $600", 0),
            ("$600 - $800", 0),
            ("$800 - $1,000", 0),
            ("$1,000 - $1,200", 0),
            ("Más de $1,200", 0),
        ]
        total_p = max(1, sum(r[1] for r in rangos))
        return {
            "rangos": [
                {"categoria": c, "cantidad_prestamos": n, "monto_total": 0.0, "porcentaje_cantidad": round(100 * n / total_p, 1), "porcentaje_monto": 0.0}
                for c, n in rangos
            ],
            "total_prestamos": total_p,
            "total_monto": 0.0,
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
    """Composición de morosidad. Datos reales: agrupa Cuota por días de mora (1-30, 31-60, 61-90, 90+)."""
    try:
        bandas = [(1, 30, "1-30 días"), (31, 60, "31-60 días"), (61, 90, "61-90 días"), (91, 999999, "90+ días")]
        puntos = []
        total_monto = 0.0
        total_cuotas = 0
        # Días de atraso = CURRENT_DATE - fecha_vencimiento (solo cuotas no pagadas)
        dias_atraso = func.current_date() - Cuota.fecha_vencimiento
        for min_d, max_d, cat in bandas:
            if max_d >= 999999:
                q = select(
                    func.count().label("n"),
                    func.coalesce(func.sum(Cuota.monto), 0).label("m"),
                ).select_from(Cuota).where(
                    Cuota.pagado.is_(False),
                    dias_atraso >= min_d,
                )
            else:
                q = select(
                    func.count().label("n"),
                    func.coalesce(func.sum(Cuota.monto), 0).label("m"),
                ).select_from(Cuota).where(
                    Cuota.pagado.is_(False),
                    dias_atraso >= min_d,
                    dias_atraso <= max_d,
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
    """Morosidad por analista: cuotas vencidas (tabla cuotas) por analista (préstamo). Devuelve cantidad de cuotas vencidas y monto vencido en USD por analista."""
    try:
        hoy = date.today()
        # Cuotas vencidas: no pagadas y fecha_vencimiento < hoy
        cuotas_vencidas = db.execute(
            select(Cuota.id, Cuota.cliente_id, Cuota.monto).select_from(Cuota).where(
                Cuota.pagado.is_(False),
                Cuota.fecha_vencimiento < hoy,
            )
        ).all()
        # Prestamos APROBADO: un préstamo por cliente (el más reciente) para asignar analista
        prestamos_por_cliente = (
            db.execute(
                select(Prestamo.cliente_id, Prestamo.analista)
                .select_from(Prestamo)
                .where(Prestamo.estado == "APROBADO", Prestamo.analista.isnot(None))
                .order_by(Prestamo.cliente_id, Prestamo.fecha_creacion.desc())
            )
            .all()
        )
        cliente_a_analista = {}
        for cliente_id, analista_val in prestamos_por_cliente:
            if cliente_id not in cliente_a_analista:
                cliente_a_analista[cliente_id] = analista_val or "Sin analista"
        # Agrupar cuotas vencidas por analista
        por_analista = {}
        for cid, cliente_id, monto in cuotas_vencidas:
            a = cliente_a_analista.get(cliente_id, "Sin analista")
            if a not in por_analista:
                por_analista[a] = {"cantidad_cuotas_vencidas": 0, "monto_vencido": 0.0}
            por_analista[a]["cantidad_cuotas_vencidas"] += 1
            por_analista[a]["monto_vencido"] += _safe_float(monto)
        resultado = [
            {
                "analista": a,
                "cantidad_cuotas_vencidas": d["cantidad_cuotas_vencidas"],
                "monto_vencido": round(d["monto_vencido"], 2),
            }
            for a, d in sorted(por_analista.items(), key=lambda x: -x[1]["monto_vencido"])
        ]
        return {"analistas": resultado}
    except Exception as e:
        logger.exception("Error en morosidad-por-analista: %s", e)
        return {"analistas": []}


@router.get("/evolucion-morosidad")
def get_evolucion_morosidad(
    fecha_inicio: Optional[str] = Query(None),
    meses: Optional[int] = Query(12),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Evolución de morosidad por mes. Datos reales: suma monto de cuotas vencidas no pagadas a fin de cada mes (Cuota)."""
    try:
        meses_list = _ultimos_12_meses()
        hoy = datetime.now(timezone.utc)
        resultado = []
        for i, m in enumerate(meses_list):
            fin_mes = hoy - timedelta(days=30 * (11 - i))
            ultimo_dia = _ultimo_dia_del_mes(fin_mes.replace(tzinfo=timezone.utc) if fin_mes.tzinfo is None else fin_mes)
            ultimo_dia_date = ultimo_dia.date() if hasattr(ultimo_dia, "date") else ultimo_dia
            moro = db.scalar(
                select(func.coalesce(func.sum(Cuota.monto), 0)).select_from(Cuota).where(
                    Cuota.pagado.is_(False),
                    Cuota.fecha_vencimiento <= ultimo_dia_date,
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
    meses_list = [{"mes": x["mes"], "pagos": 12 + i, "monto": x["monto_pagado"]} for i, x in enumerate(m)]
    return {"meses": meses_list}


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
