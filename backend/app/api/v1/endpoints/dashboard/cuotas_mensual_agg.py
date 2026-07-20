"""Agregaciones mensuales de cuotas en consultas batch (evita N*3 queries por mes)."""
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import Date, Integer, and_, case, cast, func, or_, select
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.prestamo import Prestamo

from .utils import (
    _etiquetas_12_meses,
    _meses_desde_rango,
    _primer_ultimo_dia_mes,
    _safe_float,
)

# Cartera operativa del gráfico Evolución Mensual (cuotas): aprobado + liquidado.
_ESTADOS_PRESTAMO_EVOLUCION = ("APROBADO", "LIQUIDADO")
_prestamo_en_evolucion = Prestamo.estado.in_(_ESTADOS_PRESTAMO_EVOLUCION)


def _resolver_meses_con_fechas(
    fecha_inicio: Optional[str],
    fecha_fin: Optional[str],
) -> list[dict]:
    if fecha_inicio and fecha_fin:
        try:
            inicio = date.fromisoformat(fecha_inicio)
            fin = date.fromisoformat(fecha_fin)
            if inicio <= fin:
                meses_raw = _meses_desde_rango(inicio, fin)
            else:
                meses_raw = _etiquetas_12_meses()
        except ValueError:
            meses_raw = _etiquetas_12_meses()
    else:
        meses_raw = _etiquetas_12_meses()

    meses_out: list[dict] = []
    for i, m in enumerate(meses_raw):
        if "year" in m and "month" in m:
            y, mo = m["year"], m["month"]
            inicio_d = date(y, mo, 1)
            if mo == 12:
                fin_d = date(y, 12, 31)
            else:
                fin_d = date(y, mo + 1, 1) - timedelta(days=1)
        else:
            hoy = datetime.now(timezone.utc)
            fin_mes = hoy - timedelta(days=30 * (len(meses_raw) - 1 - i))
            if fin_mes.tzinfo is None:
                fin_mes = fin_mes.replace(tzinfo=timezone.utc)
            inicio_d, fin_d = _primer_ultimo_dia_mes(fin_mes)
        meses_out.append({**m, "inicio_d": inicio_d, "fin_d": fin_d})
    return meses_out


def _mes_key(year: int, month: int) -> tuple[int, int]:
    return (int(year), int(month))


def _sum_cuotas_por_mes_vencimiento(
    db: Session,
    min_d: date,
    max_d: date,
    *,
    solo_pagadas: bool,
) -> dict[tuple[int, int], float]:
    """
    Suma Cuota.monto agrupada por mes calendario de fecha_vencimiento.

    Si solo_pagadas=True (barra verde / cobrado del mes): exige fecha_pago
    informada y en el **mismo mes calendario** que fecha_vencimiento.
    No incluye pagos tardios ni anticipados de otro mes (esos van a atrasos
    o anticipados segun el caso).
    """
    anio = cast(func.extract("year", Cuota.fecha_vencimiento), Integer)
    mes_num = cast(func.extract("month", Cuota.fecha_vencimiento), Integer)
    conds = [
        _prestamo_en_evolucion,
        Cuota.fecha_vencimiento >= min_d,
        Cuota.fecha_vencimiento <= max_d,
    ]
    if solo_pagadas:
        # Mismo mes de vencimiento y de pago (no "pagada en cualquier fecha").
        inicio_mes_venc = cast(func.date_trunc("month", Cuota.fecha_vencimiento), Date)
        inicio_mes_pago = cast(func.date_trunc("month", Cuota.fecha_pago), Date)
        conds.append(Cuota.fecha_pago.isnot(None))
        conds.append(inicio_mes_pago == inicio_mes_venc)

    stmt = (
        select(
            anio.label("anio"),
            mes_num.label("mes"),
            func.coalesce(func.sum(Cuota.monto), 0).label("total"),
        )
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(and_(*conds))
        .group_by(anio, mes_num)
    )
    out: dict[tuple[int, int], float] = {}
    for row in db.execute(stmt).all():
        if row.anio is None or row.mes is None:
            continue
        out[_mes_key(int(row.anio), int(row.mes))] = _safe_float(row.total)
    return out


def _sum_pagos_atrasos_por_mes_pago(
    db: Session,
    min_d: date,
    max_d: date,
) -> dict[tuple[int, int], float]:
    """Cuotas vencidas antes del mes de pago, agrupadas por mes calendario de fecha_pago."""
    anio = cast(func.extract("year", Cuota.fecha_pago), Integer)
    mes_num = cast(func.extract("month", Cuota.fecha_pago), Integer)
    inicio_mes_pago = cast(func.date_trunc("month", Cuota.fecha_pago), Date)

    stmt = (
        select(
            anio.label("anio"),
            mes_num.label("mes"),
            func.coalesce(func.sum(Cuota.monto), 0).label("total"),
        )
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(
            _prestamo_en_evolucion,
            Cuota.fecha_pago.isnot(None),
            Cuota.fecha_pago >= min_d,
            Cuota.fecha_pago <= max_d,
            Cuota.fecha_vencimiento < inicio_mes_pago,
        )
        .group_by(anio, mes_num)
    )
    out: dict[tuple[int, int], float] = {}
    for row in db.execute(stmt).all():
        if row.anio is None or row.mes is None:
            continue
        out[_mes_key(int(row.anio), int(row.mes))] = _safe_float(row.total)
    return out


def _sum_pagos_anticipados_por_mes_pago(
    db: Session,
    min_d: date,
    max_d: date,
) -> dict[tuple[int, int], float]:
    """Pago en el mes con vencimiento en un mes posterior (anticipos)."""
    anio = cast(func.extract("year", Cuota.fecha_pago), Integer)
    mes_num = cast(func.extract("month", Cuota.fecha_pago), Integer)
    inicio_mes_pago = cast(func.date_trunc("month", Cuota.fecha_pago), Date)
    inicio_mes_venc = cast(func.date_trunc("month", Cuota.fecha_vencimiento), Date)

    stmt = (
        select(
            anio.label("anio"),
            mes_num.label("mes"),
            func.coalesce(func.sum(Cuota.monto), 0).label("total"),
        )
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(
            _prestamo_en_evolucion,
            Cuota.fecha_pago.isnot(None),
            Cuota.fecha_pago >= min_d,
            Cuota.fecha_pago <= max_d,
            inicio_mes_venc > inicio_mes_pago,
        )
        .group_by(anio, mes_num)
    )
    out: dict[tuple[int, int], float] = {}
    for row in db.execute(stmt).all():
        if row.anio is None or row.mes is None:
            continue
        out[_mes_key(int(row.anio), int(row.mes))] = _safe_float(row.total)
    return out


def _sum_pagos_no_conciliados_por_categoria(
    db: Session,
    min_d: date,
    max_d: date,
) -> tuple[dict[tuple[int, int], float], dict[tuple[int, int], float]]:
    """
    Pagos con conciliado=False (excl. anulados/duplicados), por mes de fecha_pago.

    Solo montos aún no cerrados en Evolución (cuota sin fecha_pago), para no
    duplicar cobrado/atrasos/anticipados.

    Clasifica monto_aplicado vs vencimiento:
    - a_tiempo: mismo mes o posterior
    - atrasados: vencimiento anterior al mes del pago

    Sin cuota_pagos → monto_pagado entero a a_tiempo.
    """
    from app.models.cuota_pago import CuotaPago
    from app.models.pago import Pago

    anio = cast(func.extract("year", Pago.fecha_pago), Integer)
    mes_num = cast(func.extract("month", Pago.fecha_pago), Integer)
    inicio_mes_pago = cast(func.date_trunc("month", Pago.fecha_pago), Date)
    inicio_mes_venc = cast(func.date_trunc("month", Cuota.fecha_vencimiento), Date)

    excluir_estados = ("ANULADO", "ANULADO_IMPORT", "DUPLICADO")
    base_pago = and_(
        Pago.conciliado.is_(False),
        Pago.fecha_pago >= min_d,
        Pago.fecha_pago <= max_d,
        or_(Pago.estado.is_(None), Pago.estado.notin_(excluir_estados)),
    )

    a_tiempo_expr = and_(
        Cuota.fecha_pago.is_(None),
        or_(inicio_mes_venc == inicio_mes_pago, inicio_mes_venc > inicio_mes_pago),
    )
    atrasados_expr = and_(
        Cuota.fecha_pago.is_(None),
        Cuota.fecha_vencimiento < inicio_mes_pago,
    )

    stmt_aplic = (
        select(
            anio.label("anio"),
            mes_num.label("mes"),
            func.coalesce(
                func.sum(
                    case((a_tiempo_expr, CuotaPago.monto_aplicado), else_=0)
                ),
                0,
            ).label("a_tiempo"),
            func.coalesce(
                func.sum(
                    case((atrasados_expr, CuotaPago.monto_aplicado), else_=0)
                ),
                0,
            ).label("atrasados"),
        )
        .select_from(CuotaPago)
        .join(Pago, Pago.id == CuotaPago.pago_id)
        .join(Cuota, Cuota.id == CuotaPago.cuota_id)
        .where(base_pago)
        .group_by(anio, mes_num)
    )

    a_tiempo_by: dict[tuple[int, int], float] = {}
    atrasados_by: dict[tuple[int, int], float] = {}
    for row in db.execute(stmt_aplic).all():
        if row.anio is None or row.mes is None:
            continue
        key = _mes_key(int(row.anio), int(row.mes))
        a_tiempo_by[key] = _safe_float(row.a_tiempo)
        atrasados_by[key] = _safe_float(row.atrasados)

    pagos_con_cp = select(CuotaPago.pago_id).distinct()
    stmt_sin = (
        select(
            anio.label("anio"),
            mes_num.label("mes"),
            func.coalesce(func.sum(Pago.monto_pagado), 0).label("total"),
        )
        .select_from(Pago)
        .where(base_pago, ~Pago.id.in_(pagos_con_cp))
        .group_by(anio, mes_num)
    )
    for row in db.execute(stmt_sin).all():
        if row.anio is None or row.mes is None:
            continue
        key = _mes_key(int(row.anio), int(row.mes))
        a_tiempo_by[key] = a_tiempo_by.get(key, 0.0) + _safe_float(row.total)

    return a_tiempo_by, atrasados_by


def _fetch_agregados_mensuales_cuotas(
    db: Session,
    meses: list[dict],
) -> tuple[
    dict[tuple[int, int], float],
    dict[tuple[int, int], float],
    dict[tuple[int, int], float],
    dict[tuple[int, int], float],
    dict[tuple[int, int], float],
    dict[tuple[int, int], float],
]:
    """
    Devuelve por (anio, mes):
    cartera, cobrado, atrasos, anticipados,
    no_conciliados_a_tiempo, no_conciliados_atrasados.
    """
    if not meses:
        return {}, {}, {}, {}, {}, {}
    min_d = min(m["inicio_d"] for m in meses)
    max_d = max(m["fin_d"] for m in meses)
    cartera_by = _sum_cuotas_por_mes_vencimiento(db, min_d, max_d, solo_pagadas=False)
    cobrado_by = _sum_cuotas_por_mes_vencimiento(db, min_d, max_d, solo_pagadas=True)
    atrasos_by = _sum_pagos_atrasos_por_mes_pago(db, min_d, max_d)
    anticipados_by = _sum_pagos_anticipados_por_mes_pago(db, min_d, max_d)
    no_conc_a_tiempo_by, no_conc_atrasados_by = _sum_pagos_no_conciliados_por_categoria(
        db, min_d, max_d
    )
    return (
        cartera_by,
        cobrado_by,
        atrasos_by,
        anticipados_by,
        no_conc_a_tiempo_by,
        no_conc_atrasados_by,
    )


def _mes_lookup(m: dict) -> tuple[int, int]:
    return _mes_key(m["year"], m["month"])
