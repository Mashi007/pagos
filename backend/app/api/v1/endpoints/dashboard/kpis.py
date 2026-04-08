"""
Dashboard KPIs: opciones-filtros, kpis-principales, admin.

Criterios de fecha en prestamos: la mayoria de agregados que filtran por periodo
usan `prestamo_fecha_referencia_negocio` (coalesce: fecha_base_calculo,
date(fecha_aprobacion), fecha_requerimiento) para alinear con el inicio de cuotas
cuando en datos historicos la base y la aprobacion difieren. Los conteos
explicitos por mes de aprobacion administrativa deben usar
`prestamo_fecha_referencia_por_aprobacion` (aprobacion primero).
"""
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Date, and_, case, cast, func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
from app.core.deps import get_current_user
from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.modelo_vehiculo import ModeloVehiculo
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.services.cuota_estado import hoy_negocio
from app.services.prestamos.prestamo_fecha_referencia_query import (
    prestamo_fecha_referencia_negocio,
)

from .utils import (
    _CACHE_KPIS,
    _CACHE_OPCIONES_FILTROS,
    _DASHBOARD_ADMIN_CACHE,
    _lock,
    _modelo_label_dashboard_expr,
    _next_refresh_local,
    _OPCIONES_FILTROS_TTL_SEC,
    _safe_float,
    _sanitize_filter_string,
    _kpi,
    _etiquetas_12_meses,
    _rango_y_anterior,
    _ultimo_dia_del_mes,
    _primer_ultimo_dia_mes,
    _meses_desde_rango,
    _parse_fechas_concesionario,
)

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])


def _monto_pago_usd_sql():
    """Expresión SQL: monto del pago en USD (BS con tasa del registro vs monto_pagado)."""
    moneda_bs = func.lower(func.trim(Pago.moneda_registro)) == "bs"
    tasa_ok = and_(
        Pago.tasa_cambio_bs_usd.isnot(None),
        Pago.tasa_cambio_bs_usd > 0,
    )
    return case(
        (and_(moneda_bs, Pago.monto_bs_original.isnot(None), tasa_ok), Pago.monto_bs_original / Pago.tasa_cambio_bs_usd),
        else_=Pago.monto_pagado,
    )


def _sum_monto_cuotas_vencen_dia_conciliadas_mismo_dia_caracas(
    db: Session,
    dia: date,
    analista: Optional[str],
    concesionario: Optional[str],
    modelo: Optional[str],
) -> float:
    """Suma monto del **pago** en USD (monto_pagado o BS/tasa) por pagos conciliados en `dia` (Caracas).

    Solo pagos vinculados a cuotas con vencimiento = `dia`. Cada pago se cuenta una sola vez aunque
    aplique a varias cuotas con el mismo vencimiento. No incluye cuotas atrasadas (vencimiento estrictamente anterior a `dia`).
    """
    bind = db.get_bind()
    dialect = bind.dialect.name if bind is not None else "postgresql"
    fe = Pago.fecha_conciliacion
    if dialect == "postgresql":
        dia_conc = cast(
            func.timezone("America/Caracas", func.timezone("UTC", fe)),
            Date,
        )
    else:
        dia_conc = cast(fe, Date)
    producto_valido_kpi = func.nullif(
        func.nullif(func.trim(Prestamo.producto), ""),
        "Financiamiento",
    )
    modelo_lbl_expr = _modelo_label_dashboard_expr(
        producto_valido_kpi,
        incluir_sin_modelo=False,
    )
    conds = [
        Cuota.prestamo_id == Prestamo.id,
        Prestamo.cliente_id == Cliente.id,
        Prestamo.estado == "APROBADO",
        Cuota.fecha_vencimiento == dia,
        Cuota.pago_id.isnot(None),
        Cuota.pago_id == Pago.id,
        Pago.prestamo_id == Cuota.prestamo_id,
        Pago.conciliado.is_(True),
        Pago.fecha_conciliacion.isnot(None),
        dia_conc == dia,
    ]
    monto_usd = _monto_pago_usd_sql()
    inner = (
        select(Pago.id.label("pago_id"), func.max(monto_usd).label("usd"))
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .join(Pago, Cuota.pago_id == Pago.id)
        .outerjoin(ModeloVehiculo, Prestamo.modelo_vehiculo_id == ModeloVehiculo.id)
        .where(and_(*conds))
    )
    if analista:
        inner = inner.where(Prestamo.analista == analista)
    if concesionario:
        inner = inner.where(Prestamo.concesionario == concesionario)
    if modelo:
        inner = inner.where(modelo_lbl_expr == modelo)
    inner = inner.group_by(Pago.id)
    sub = inner.subquery()
    q = select(func.coalesce(func.sum(sub.c.usd), 0)).select_from(sub)
    return _safe_float(db.scalar(q) or 0)


def _sum_monto_cuotas_atrasadas_conciliadas_mismo_dia_caracas(
    db: Session,
    dia: date,
    analista: Optional[str],
    concesionario: Optional[str],
    modelo: Optional[str],
) -> float:
    """Suma monto del **pago** en USD por pagos conciliados en `dia` (Caracas) vinculados a cuotas atrasadas.

    Solo cuotas con vencimiento estrictamente anterior a `dia`. Cada pago se cuenta una sola vez.
    """
    bind = db.get_bind()
    dialect = bind.dialect.name if bind is not None else "postgresql"
    fe = Pago.fecha_conciliacion
    if dialect == "postgresql":
        dia_conc = cast(
            func.timezone("America/Caracas", func.timezone("UTC", fe)),
            Date,
        )
    else:
        dia_conc = cast(fe, Date)
    producto_valido_kpi = func.nullif(
        func.nullif(func.trim(Prestamo.producto), ""),
        "Financiamiento",
    )
    modelo_lbl_expr = _modelo_label_dashboard_expr(
        producto_valido_kpi,
        incluir_sin_modelo=False,
    )
    conds = [
        Cuota.prestamo_id == Prestamo.id,
        Prestamo.cliente_id == Cliente.id,
        Prestamo.estado == "APROBADO",
        Cuota.fecha_vencimiento < dia,
        Cuota.pago_id.isnot(None),
        Cuota.pago_id == Pago.id,
        Pago.prestamo_id == Cuota.prestamo_id,
        Pago.conciliado.is_(True),
        Pago.fecha_conciliacion.isnot(None),
        dia_conc == dia,
    ]
    monto_usd = _monto_pago_usd_sql()
    inner = (
        select(Pago.id.label("pago_id"), func.max(monto_usd).label("usd"))
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .join(Pago, Cuota.pago_id == Pago.id)
        .outerjoin(ModeloVehiculo, Prestamo.modelo_vehiculo_id == ModeloVehiculo.id)
        .where(and_(*conds))
    )
    if analista:
        inner = inner.where(Prestamo.analista == analista)
    if concesionario:
        inner = inner.where(Prestamo.concesionario == concesionario)
    if modelo:
        inner = inner.where(modelo_lbl_expr == modelo)
    inner = inner.group_by(Pago.id)
    sub = inner.subquery()
    q = select(func.coalesce(func.sum(sub.c.usd), 0)).select_from(sub)
    return _safe_float(db.scalar(q) or 0)


def _kpi_pagos_conciliados_hoy(
    db: Session,
    analista: Optional[str],
    concesionario: Optional[str],
    modelo: Optional[str],
) -> dict:
    hoy_c = hoy_negocio()
    ayer_c = hoy_c - timedelta(days=1)
    hoy_m = _sum_monto_cuotas_vencen_dia_conciliadas_mismo_dia_caracas(
        db, hoy_c, analista, concesionario, modelo
    )
    ayer_m = _sum_monto_cuotas_vencen_dia_conciliadas_mismo_dia_caracas(
        db, ayer_c, analista, concesionario, modelo
    )
    if ayer_m:
        variacion = ((hoy_m - ayer_m) / ayer_m) * 100.0
    else:
        variacion = 0.0
    return _kpi(round(hoy_m, 2), round(variacion, 1))


def _kpi_cuotas_atrasadas_conciliadas_hoy(
    db: Session,
    analista: Optional[str],
    concesionario: Optional[str],
    modelo: Optional[str],
) -> dict:
    hoy_c = hoy_negocio()
    ayer_c = hoy_c - timedelta(days=1)
    hoy_m = _sum_monto_cuotas_atrasadas_conciliadas_mismo_dia_caracas(
        db, hoy_c, analista, concesionario, modelo
    )
    ayer_m = _sum_monto_cuotas_atrasadas_conciliadas_mismo_dia_caracas(
        db, ayer_c, analista, concesionario, modelo
    )
    if ayer_m:
        variacion = ((hoy_m - ayer_m) / ayer_m) * 100.0
    else:
        variacion = 0.0
    return _kpi(round(hoy_m, 2), round(variacion, 1))


def _pagos_programados_hoy_metrics(
    db: Session,
    analista: Optional[str],
    concesionario: Optional[str],
    modelo: Optional[str],
) -> tuple[dict, float]:
    """
    Monto total (cuota.monto) de cuotas con fecha_vencimiento = día calendario Caracas;
    variación vs el día anterior; % de cuotas con vencimiento hoy que ya tienen fecha_pago.
    """
    hoy_c = hoy_negocio()
    ayer_c = hoy_c - timedelta(days=1)

    def _sum_monto_y_conteos(dia: date) -> tuple[float, int, int]:
        producto_valido_kpi = func.nullif(
            func.nullif(func.trim(Prestamo.producto), ""),
            "Financiamiento",
        )
        modelo_lbl_expr = _modelo_label_dashboard_expr(
            producto_valido_kpi,
            incluir_sin_modelo=False,
        )
        conds = [
            Cuota.prestamo_id == Prestamo.id,
            Prestamo.cliente_id == Cliente.id,
            Prestamo.estado == "APROBADO",
            Cuota.fecha_vencimiento == dia,
        ]
        if analista:
            conds.append(Prestamo.analista == analista)
        if concesionario:
            conds.append(Prestamo.concesionario == concesionario)
        if modelo:
            conds.append(modelo_lbl_expr == modelo)
        monto = _safe_float(
            db.scalar(
                select(func.coalesce(func.sum(Cuota.monto), 0))
                .select_from(Cuota)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .outerjoin(ModeloVehiculo, Prestamo.modelo_vehiculo_id == ModeloVehiculo.id)
                .where(and_(*conds))
            )
            or 0
        )
        tot = int(
            db.scalar(
                select(func.count())
                .select_from(Cuota)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .outerjoin(ModeloVehiculo, Prestamo.modelo_vehiculo_id == ModeloVehiculo.id)
                .where(and_(*conds))
            )
            or 0
        )
        pag = int(
            db.scalar(
                select(func.count())
                .select_from(Cuota)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .outerjoin(ModeloVehiculo, Prestamo.modelo_vehiculo_id == ModeloVehiculo.id)
                .where(and_(*conds, Cuota.fecha_pago.isnot(None)))
            )
            or 0
        )
        return monto, tot, pag

    m_hoy, tot_hoy, pag_hoy = _sum_monto_y_conteos(hoy_c)
    m_ayer, _, _ = _sum_monto_y_conteos(ayer_c)
    if m_ayer:
        variacion = ((m_hoy - m_ayer) / m_ayer) * 100.0
    else:
        variacion = 0.0
    pct = (float(pag_hoy) / float(tot_hoy) * 100.0) if tot_hoy else 0.0
    return _kpi(round(m_hoy, 2), round(variacion, 1)), round(pct, 1)


def _compute_kpis_principales(
    db: Session,
    fecha_inicio: Optional[str],
    fecha_fin: Optional[str],
    analista: Optional[str],
    concesionario: Optional[str],
    modelo: Optional[str],
) -> dict:
    """Calcula KPIs principales (usado por endpoint y por refresh de caché)."""
    try:
        activos = db.scalar(select(func.count()).select_from(Cliente).where(Cliente.estado == "ACTIVO")) or 0
        total_clientes = activos
        inactivos = db.scalar(select(func.count()).select_from(Cliente).where(Cliente.estado == "INACTIVO")) or 0
        finalizados = (
            db.scalar(
                select(func.count(func.distinct(Cliente.id)))
                .select_from(Cliente)
                .outerjoin(Prestamo, Prestamo.cliente_id == Cliente.id)
                .where(
                    or_(
                        Cliente.estado == "FINALIZADO",
                        Prestamo.estado == "LIQUIDADO",
                    )
                )
            )
            or 0
        )

        usar_rango = fecha_inicio and fecha_fin
        inicio = fin = None
        try:
            inicio_dt = fin_dt = inicio_ant_dt = fin_ant_dt = None
            if usar_rango:
                inicio = date.fromisoformat(fecha_inicio)
                fin = date.fromisoformat(fecha_fin)
                inicio_dt, fin_dt, inicio_ant_dt, fin_ant_dt = _rango_y_anterior(inicio, fin)
        except (ValueError, TypeError):
            usar_rango = False

        if not usar_rango:
            now_utc = datetime.now(timezone.utc)
            inicio_mes_actual = now_utc.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            fin_mes_actual = (inicio_mes_actual + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
            inicio_mes_anterior = (inicio_mes_actual - timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            fin_mes_anterior = inicio_mes_actual - timedelta(seconds=1)
            inicio_dt, fin_dt = inicio_mes_actual, fin_mes_actual
            inicio_ant_dt, fin_ant_dt = inicio_mes_anterior, fin_mes_anterior

        producto_valido_kpi = func.nullif(func.nullif(func.trim(Prestamo.producto), ""), "Financiamiento")
        modelo_lbl_expr = _modelo_label_dashboard_expr(
            producto_valido_kpi,
            incluir_sin_modelo=False,
        )

        conds_aprobacion_act = [
            Prestamo.estado == "APROBADO",
            Prestamo.fecha_aprobacion.isnot(None),
            Prestamo.fecha_aprobacion >= inicio_dt,
            Prestamo.fecha_aprobacion <= fin_dt,
        ]
        if analista:
            conds_aprobacion_act.append(Prestamo.analista == analista)
        if concesionario:
            conds_aprobacion_act.append(Prestamo.concesionario == concesionario)
        if modelo:
            conds_aprobacion_act.append(modelo_lbl_expr == modelo)

        conds_aprobacion_ant = [
            Prestamo.estado == "APROBADO",
            Prestamo.fecha_aprobacion.isnot(None),
            Prestamo.fecha_aprobacion >= inicio_ant_dt,
            Prestamo.fecha_aprobacion <= fin_ant_dt,
        ]
        if analista:
            conds_aprobacion_ant.append(Prestamo.analista == analista)
        if concesionario:
            conds_aprobacion_ant.append(Prestamo.concesionario == concesionario)
        if modelo:
            conds_aprobacion_ant.append(modelo_lbl_expr == modelo)

        total_prestamos = (
            db.scalar(
                select(func.count())
                .select_from(Prestamo)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .outerjoin(ModeloVehiculo, Prestamo.modelo_vehiculo_id == ModeloVehiculo.id)
                .where(and_(*conds_aprobacion_act))
            )
            or 0
        )

        total_prestamos_mes_anterior = (
            db.scalar(
                select(func.count())
                .select_from(Prestamo)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .outerjoin(ModeloVehiculo, Prestamo.modelo_vehiculo_id == ModeloVehiculo.id)
                .where(and_(*conds_aprobacion_ant))
            )
            or 0
        )
        if total_prestamos_mes_anterior and _safe_float(total_prestamos_mes_anterior) != 0:
            variacion_prestamos = (
                (_safe_float(total_prestamos) - _safe_float(total_prestamos_mes_anterior))
                / _safe_float(total_prestamos_mes_anterior)
            ) * 100.0
        else:
            variacion_prestamos = 0.0

        financiamiento_aprobado_mes = (
            db.scalar(
                select(func.coalesce(func.sum(Prestamo.total_financiamiento), 0))
                .select_from(Prestamo)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .outerjoin(ModeloVehiculo, Prestamo.modelo_vehiculo_id == ModeloVehiculo.id)
                .where(and_(*conds_aprobacion_act))
            )
            or 0
        )

        pagos_conciliados_hoy_kpi = _kpi_pagos_conciliados_hoy(
            db, analista, concesionario, modelo
        )

        cuotas_atrasadas_conciliadas_hoy_kpi = _kpi_cuotas_atrasadas_conciliadas_hoy(
            db, analista, concesionario, modelo
        )

        hoy = date.today()
        inicio_d = inicio_dt.date() if hasattr(inicio_dt, "date") else (inicio if usar_rango else inicio_dt.date())
        fin_d = fin_dt.date() if hasattr(fin_dt, "date") else (fin if usar_rango else fin_dt.date())
        conds_moro = [
            Cuota.prestamo_id == Prestamo.id,
            Prestamo.cliente_id == Cliente.id,
            Prestamo.estado == "APROBADO",
            Cuota.fecha_pago.is_(None),
            Cuota.fecha_vencimiento < hoy,
            Cuota.fecha_vencimiento >= inicio_d,
            Cuota.fecha_vencimiento <= fin_d,
        ]
        if analista:
            conds_moro.append(Prestamo.analista == analista)
        if concesionario:
            conds_moro.append(Prestamo.concesionario == concesionario)
        if modelo:
            conds_moro.append(modelo_lbl_expr == modelo)
        morosidad_actual = _safe_float(
            db.scalar(
                select(func.coalesce(func.sum(Cuota.monto), 0))
                .select_from(Cuota)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .outerjoin(ModeloVehiculo, Prestamo.modelo_vehiculo_id == ModeloVehiculo.id)
                .where(and_(*conds_moro))
            )
        )
        inicio_ant_d = inicio_ant_dt.date() if hasattr(inicio_ant_dt, "date") else inicio_ant_dt
        fin_ant_d = fin_ant_dt.date() if hasattr(fin_ant_dt, "date") else fin_ant_dt
        conds_moro_ant = [
            Cuota.prestamo_id == Prestamo.id,
            Prestamo.cliente_id == Cliente.id,
            Prestamo.estado == "APROBADO",
            Cuota.fecha_pago.is_(None),
            Cuota.fecha_vencimiento < hoy,
            Cuota.fecha_vencimiento >= inicio_ant_d,
            Cuota.fecha_vencimiento <= fin_ant_d,
        ]
        if analista:
            conds_moro_ant.append(Prestamo.analista == analista)
        if concesionario:
            conds_moro_ant.append(Prestamo.concesionario == concesionario)
        if modelo:
            conds_moro_ant.append(modelo_lbl_expr == modelo)
        morosidad_mes_anterior = _safe_float(
            db.scalar(
                select(func.coalesce(func.sum(Cuota.monto), 0))
                .select_from(Cuota)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .outerjoin(ModeloVehiculo, Prestamo.modelo_vehiculo_id == ModeloVehiculo.id)
                .where(and_(*conds_moro_ant))
            )
        )
        if morosidad_mes_anterior and morosidad_mes_anterior != 0:
            variacion_morosidad = ((morosidad_actual - morosidad_mes_anterior) / morosidad_mes_anterior) * 100.0
        else:
            variacion_morosidad = 0.0

        pagos_programados_hoy_kpi, porcentaje_cuotas_pagadas_hoy = _pagos_programados_hoy_metrics(
            db, analista, concesionario, modelo
        )

        return {
            "total_prestamos": {
                **_kpi(_safe_float(total_prestamos), round(variacion_prestamos, 1)),
                "financiamiento_total": round(_safe_float(financiamiento_aprobado_mes), 2),
            },
            "pagos_conciliados_hoy": pagos_conciliados_hoy_kpi,
            "cuotas_atrasadas_conciliadas_hoy": cuotas_atrasadas_conciliadas_hoy_kpi,
            "total_clientes": _kpi(_safe_float(total_clientes), 0.0),
            "clientes_por_estado": {
                "activos": _kpi(_safe_float(activos), 0.0),
                "inactivos": _kpi(_safe_float(inactivos), 0.0),
                "finalizados": _kpi(_safe_float(finalizados), 0.0),
            },
            "total_morosidad_usd": _kpi(round(morosidad_actual, 2), round(variacion_morosidad, 1)),
            "pagos_programados_hoy": pagos_programados_hoy_kpi,
            "porcentaje_cuotas_pagadas_hoy": porcentaje_cuotas_pagadas_hoy,
        }
    except Exception as e:
        logger.exception("Error en kpis-principales: %s", e)
        try:
            db.rollback()
        except Exception:
            pass
        raise




def _compute_kpis_dashboard_flat(
    db: Session,
    fecha_inicio: Optional[str],
    fecha_fin: Optional[str],
    analista: Optional[str],
    concesionario: Optional[str],
    modelo: Optional[str],
) -> dict:
    """Totales de financiamiento por estado (activo / inactivo / liquidado) para GET /kpis/dashboard."""
    analista = _sanitize_filter_string(analista)
    concesionario = _sanitize_filter_string(concesionario)
    modelo = _sanitize_filter_string(modelo)
    inicio, fin = _parse_fechas_concesionario(fecha_inicio, fecha_fin)

    producto_valido = func.nullif(func.nullif(func.trim(Prestamo.producto), ""), "Financiamiento")
    modelo_lbl = _modelo_label_dashboard_expr(producto_valido, incluir_sin_modelo=False)

    fecha_ref = prestamo_fecha_referencia_negocio()
    conds = [
        Prestamo.estado.in_(["APROBADO", "LIQUIDADO"]),
        fecha_ref >= inicio,
        fecha_ref <= fin,
    ]
    if analista:
        conds.append(Prestamo.analista == analista)
    if concesionario:
        conds.append(Prestamo.concesionario == concesionario)
    if modelo:
        conds.append(modelo_lbl == modelo)

    tf = func.coalesce(Prestamo.total_financiamiento, 0)
    sum_activo = func.coalesce(
        func.sum(
            case(
                (and_(Prestamo.estado == "APROBADO", Cliente.estado == "ACTIVO"), tf),
                else_=0,
            )
        ),
        0,
    )
    sum_inactivo = func.coalesce(
        func.sum(
            case(
                (and_(Prestamo.estado == "APROBADO", Cliente.estado == "INACTIVO"), tf),
                else_=0,
            )
        ),
        0,
    )
    sum_finalizado = func.coalesce(
        func.sum(case((Prestamo.estado == "LIQUIDADO", tf), else_=0)),
        0,
    )
    q = (
        select(
            sum_activo.label("tf_activo"),
            sum_inactivo.label("tf_inactivo"),
            sum_finalizado.label("tf_finalizado"),
            func.count(Prestamo.id).label("n_prestamos"),
        )
        .select_from(Prestamo)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .outerjoin(ModeloVehiculo, Prestamo.modelo_vehiculo_id == ModeloVehiculo.id)
        .where(and_(*conds))
    )
    row = db.execute(q).one()
    ta = _safe_float(row.tf_activo)
    ti = _safe_float(row.tf_inactivo)
    tfi = _safe_float(row.tf_finalizado)
    total_tf = ta + ti + tfi
    n_prestamos = int(row.n_prestamos or 0)
    return {
        "total_financiamiento": round(total_tf, 2),
        "total_financiamiento_activo": round(ta, 2),
        "total_financiamiento_inactivo": round(ti, 2),
        "total_financiamiento_finalizado": round(tfi, 2),
        "total_prestamos": n_prestamos,
    }


@router.get("/dashboard")
def get_kpis_dashboard(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """KPIs planos de financiamiento (usado por DashboardFinanciamiento: /api/v1/kpis/dashboard)."""
    try:
        return _compute_kpis_dashboard_flat(
            db, fecha_inicio, fecha_fin, analista, concesionario, modelo
        )
    except Exception as e:
        logger.exception("Error en GET /kpis/dashboard: %s", e)
        try:
            db.rollback()
        except Exception:
            pass
        return {
            "total_financiamiento": 0.0,
            "total_financiamiento_activo": 0.0,
            "total_financiamiento_inactivo": 0.0,
            "total_financiamiento_finalizado": 0.0,
            "total_prestamos": 0,
        }


@router.get("/opciones-filtros")
def get_opciones_filtros(db: Session = Depends(get_db)):
    """Opciones para filtros desde BD: analistas, concesionarios, modelos. Caché 5 min."""
    now = datetime.now()
    with _lock:
        cached = _CACHE_OPCIONES_FILTROS.get("data")
        refreshed = _CACHE_OPCIONES_FILTROS.get("refreshed_at")
    if cached is not None and refreshed is not None:
        age_sec = (now - refreshed).total_seconds()
        if age_sec < _OPCIONES_FILTROS_TTL_SEC:
            return cached
    try:
        analistas = [r[0] for r in db.execute(
            select(Prestamo.analista).select_from(Prestamo).join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(Prestamo.estado == "APROBADO", Prestamo.analista.isnot(None))
            .distinct()
        ).all() if r[0]]
        concesionarios = [r[0] for r in db.execute(
            select(Prestamo.concesionario).select_from(Prestamo).join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(Prestamo.estado == "APROBADO", Prestamo.concesionario.isnot(None))
            .distinct()
        ).all() if r[0]]
        producto_valido = func.nullif(func.nullif(func.trim(Prestamo.producto), ""), "Financiamiento")
        modelo_nombre = _modelo_label_dashboard_expr(
            producto_valido,
            incluir_sin_modelo=False,
        )
        modelos = [r[0] for r in db.execute(
            select(modelo_nombre)
            .select_from(Prestamo)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .outerjoin(ModeloVehiculo, Prestamo.modelo_vehiculo_id == ModeloVehiculo.id)
            .where(Prestamo.estado == "APROBADO", modelo_nombre.isnot(None))
            .distinct()
        ).all() if r[0]]
        data = {"analistas": analistas, "concesionarios": concesionarios, "modelos": modelos}
        with _lock:
            _CACHE_OPCIONES_FILTROS["data"] = data
            _CACHE_OPCIONES_FILTROS["refreshed_at"] = datetime.now()
        return data
    except Exception:
        return {"analistas": [], "concesionarios": [], "modelos": []}


@router.get("/kpis-principales")
def get_kpis_principales(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """KPIs principales. Con caché 2 veces/día (1:00, 13:00) cuando no se envían fechas ni filtros."""
    analista = _sanitize_filter_string(analista)
    concesionario = _sanitize_filter_string(concesionario)
    modelo = _sanitize_filter_string(modelo)
    use_cache = not (fecha_inicio or fecha_fin or analista or concesionario or modelo)
    if use_cache:
        with _lock:
            cached = _CACHE_KPIS["data"]
            refreshed = _CACHE_KPIS.get("refreshed_at")
        if cached is not None and refreshed is not None and datetime.now() < _next_refresh_local():
            # KPI diario: recalcular siempre para reflejar el día actual (el resto sigue en caché).
            merged = dict(cached)
            merged["pagos_conciliados_hoy"] = _kpi_pagos_conciliados_hoy(
                db, analista, concesionario, modelo
            )
            merged["cuotas_atrasadas_conciliadas_hoy"] = _kpi_cuotas_atrasadas_conciliadas_hoy(
                db, analista, concesionario, modelo
            )
            k_prog, pct_prog = _pagos_programados_hoy_metrics(
                db, analista, concesionario, modelo
            )
            merged["pagos_programados_hoy"] = k_prog
            merged["porcentaje_cuotas_pagadas_hoy"] = pct_prog
            return merged
    data = _compute_kpis_principales(db, fecha_inicio, fecha_fin, analista, concesionario, modelo)
    if use_cache:
        with _lock:
            _CACHE_KPIS["data"] = data
            _CACHE_KPIS["refreshed_at"] = datetime.now()
    return data


def _compute_dashboard_admin(
    db: Session,
    fecha_inicio: Optional[str],
    fecha_fin: Optional[str],
) -> dict:
    """Calcula la respuesta de dashboard/admin (evolucion_mensual desde cuotas)."""
    if fecha_inicio and fecha_fin:
        try:
            inicio = date.fromisoformat(fecha_inicio)
            fin = date.fromisoformat(fecha_fin)
            if inicio <= fin:
                meses = _meses_desde_rango(inicio, fin)
            else:
                meses = _etiquetas_12_meses()
        except ValueError:
            meses = _etiquetas_12_meses()
    else:
        meses = _etiquetas_12_meses()

    evolucion = []
    try:
        for i, m in enumerate(meses):
            if "year" in m and "month" in m:
                y, mo = m["year"], m["month"]
                inicio_d = date(y, mo, 1)
                if mo == 12:
                    fin_d = date(y, 12, 31)
                else:
                    fin_d = date(y, mo + 1, 1) - timedelta(days=1)
            else:
                hoy = datetime.now(timezone.utc)
                fin_mes = hoy - timedelta(days=30 * (len(meses) - 1 - i))
                if fin_mes.tzinfo is None:
                    fin_mes = fin_mes.replace(tzinfo=timezone.utc)
                inicio_d, fin_d = _primer_ultimo_dia_mes(fin_mes)
            # PROGRAMADOS (cartera): suma de cuotas con vencimiento en este mes
            cartera = db.scalar(
                select(func.coalesce(func.sum(Cuota.monto), 0))
                .select_from(Cuota)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(
                    Prestamo.estado == "APROBADO",
                    Cuota.fecha_vencimiento >= inicio_d,
                    Cuota.fecha_vencimiento <= fin_d,
                )
            ) or 0
            
            # CONCILIADOS DEL MES: cuotas con vencimiento en este mes y ya pagadas (fecha_pago no nula).
            # No incluye cobros de cuotas vencidas en meses anteriores (eso va en pagos_atrasos).
            cobrado = db.scalar(
                select(func.coalesce(func.sum(Cuota.monto), 0))
                .select_from(Cuota)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(
                    Prestamo.estado == "APROBADO",
                    Cuota.fecha_vencimiento >= inicio_d,
                    Cuota.fecha_vencimiento <= fin_d,
                    Cuota.fecha_pago.isnot(None),
                )
            ) or 0

            # Pagos de meses anteriores: vencieron antes de este mes pero se pagaron dentro del mes (solo para la barra naranja).
            pagos_atrasos = db.scalar(
                select(func.coalesce(func.sum(Cuota.monto), 0))
                .select_from(Cuota)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(
                    Prestamo.estado == "APROBADO",
                    Cuota.fecha_vencimiento < inicio_d,
                    Cuota.fecha_pago >= inicio_d,
                    Cuota.fecha_pago <= fin_d,
                    Cuota.fecha_pago.isnot(None),
                )
            ) or 0

            cartera_f = _safe_float(cartera)
            cobrado_f = _safe_float(cobrado)
            pagos_atrasos_f = _safe_float(pagos_atrasos)

            # Cuentas por cobrar (línea): únicamente programados del mes menos conciliados del mes.
            # pagos_atrasos no participa en este cálculo.
            cuentas_por_cobrar_f = cartera_f - cobrado_f
            evolucion.append({
                "mes": m["mes"],
                "cartera": cartera_f,
                "cobrado": cobrado_f,
                "pagos_atrasos": pagos_atrasos_f,
                "cuentas_por_cobrar": cuentas_por_cobrar_f,
            })
        origen = "bd"
    except Exception as e:
        logger.exception("Error en dashboard admin (evolucion desde cuotas): %s", e)
        evolucion = [
            {
                "mes": m["mes"],
                "cartera": 0.0,
                "cobrado": 0.0,
                "pagos_atrasos": 0.0,
                "cuentas_por_cobrar": 0.0,
            }
            for m in meses
        ]
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


def _compute_analisis_cuentas_por_cobrar(
    db: Session,
    fecha_inicio: Optional[str],
    fecha_fin: Optional[str],
) -> dict:
    """Calcula análisis de cuentas por cobrar: lo programado vs pagos de atrasos."""
    if fecha_inicio and fecha_fin:
        try:
            inicio = date.fromisoformat(fecha_inicio)
            fin = date.fromisoformat(fecha_fin)
            if inicio <= fin:
                meses = _meses_desde_rango(inicio, fin)
            else:
                meses = _etiquetas_12_meses()
        except ValueError:
            meses = _etiquetas_12_meses()
    else:
        meses = _etiquetas_12_meses()

    analisis = []
    try:
        for i, m in enumerate(meses):
            if "year" in m and "month" in m:
                y, mo = m["year"], m["month"]
                inicio_d = date(y, mo, 1)
                if mo == 12:
                    fin_d = date(y, 12, 31)
                else:
                    fin_d = date(y, mo + 1, 1) - timedelta(days=1)
            else:
                hoy = datetime.now(timezone.utc)
                fin_mes = hoy - timedelta(days=30 * (len(meses) - 1 - i))
                if fin_mes.tzinfo is None:
                    fin_mes = fin_mes.replace(tzinfo=timezone.utc)
                inicio_d, fin_d = _primer_ultimo_dia_mes(fin_mes)

            # 1. LO QUE DEBERÍA COBRARSE: Cuotas programadas en este mes
            cartera = db.scalar(
                select(func.coalesce(func.sum(Cuota.monto), 0))
                .select_from(Cuota)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(
                    Prestamo.estado == "APROBADO",
                    Cuota.fecha_vencimiento >= inicio_d,
                    Cuota.fecha_vencimiento <= fin_d,
                )
            ) or 0

            # Cobrado del mes (misma regla que evolución mensual /admin): vencimiento en el mes y cuota pagada
            cobrado_mes = db.scalar(
                select(func.coalesce(func.sum(Cuota.monto), 0))
                .select_from(Cuota)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(
                    Prestamo.estado == "APROBADO",
                    Cuota.fecha_vencimiento >= inicio_d,
                    Cuota.fecha_vencimiento <= fin_d,
                    Cuota.fecha_pago.isnot(None),
                )
            ) or 0

            # 2. PAGOS DE MESES ANTERIORES: Cuotas que vencieron ANTES de este mes pero se pagaron EN este mes
            pagos_atrasos = db.scalar(
                select(func.coalesce(func.sum(Cuota.monto), 0))
                .select_from(Cuota)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(
                    Prestamo.estado == "APROBADO",
                    Cuota.fecha_vencimiento < inicio_d,  # Vencimiento ANTES de este mes
                    Cuota.fecha_pago >= inicio_d,        # Pero se pagó EN este mes
                    Cuota.fecha_pago <= fin_d,
                    Cuota.fecha_pago.isnot(None),
                )
            ) or 0

            cartera_f = _safe_float(cartera)
            cobrado_f = _safe_float(cobrado_mes)
            pagos_atrasos_f = _safe_float(pagos_atrasos)

            analisis.append({
                "mes": m["mes"],
                "cartera": cartera_f,
                "cobrado_mes": cobrado_f,
                "pagos_atrasos": pagos_atrasos_f,
            })
        origen = "bd"
    except Exception as e:
        logger.exception("Error en analisis_cuentas_por_cobrar: %s", e)
        analisis = [
            {"mes": m["mes"], "cartera": 0.0, "cobrado_mes": 0.0, "pagos_atrasos": 0.0}
            for m in meses
        ]
        origen = "bd"

    return {
        "analisis": analisis,
        "origen": origen,
    }


def _compute_tendencia_programado_vs_total_cobrado(
    db: Session,
    fecha_inicio: Optional[str],
    fecha_fin: Optional[str],
) -> dict:
    """Línea 1: cuotas programadas (vencimiento en el mes). Línea 2: cobrado del mes + atrasos cobrados en el mes."""
    if fecha_inicio and fecha_fin:
        try:
            inicio = date.fromisoformat(fecha_inicio)
            fin = date.fromisoformat(fecha_fin)
            if inicio <= fin:
                meses = _meses_desde_rango(inicio, fin)
            else:
                meses = _etiquetas_12_meses()
        except ValueError:
            meses = _etiquetas_12_meses()
    else:
        meses = _etiquetas_12_meses()

    series = []
    try:
        for i, m in enumerate(meses):
            if "year" in m and "month" in m:
                y, mo = m["year"], m["month"]
                inicio_d = date(y, mo, 1)
                if mo == 12:
                    fin_d = date(y, 12, 31)
                else:
                    fin_d = date(y, mo + 1, 1) - timedelta(days=1)
            else:
                hoy = datetime.now(timezone.utc)
                fin_mes = hoy - timedelta(days=30 * (len(meses) - 1 - i))
                if fin_mes.tzinfo is None:
                    fin_mes = fin_mes.replace(tzinfo=timezone.utc)
                inicio_d, fin_d = _primer_ultimo_dia_mes(fin_mes)

            programadas = db.scalar(
                select(func.coalesce(func.sum(Cuota.monto), 0))
                .select_from(Cuota)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(
                    Prestamo.estado == "APROBADO",
                    Cuota.fecha_vencimiento >= inicio_d,
                    Cuota.fecha_vencimiento <= fin_d,
                )
            ) or 0

            conciliados_mes = db.scalar(
                select(func.coalesce(func.sum(Cuota.monto), 0))
                .select_from(Cuota)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(
                    Prestamo.estado == "APROBADO",
                    Cuota.fecha_vencimiento >= inicio_d,
                    Cuota.fecha_vencimiento <= fin_d,
                    Cuota.fecha_pago.isnot(None),
                )
            ) or 0

            pagos_meses_anteriores = db.scalar(
                select(func.coalesce(func.sum(Cuota.monto), 0))
                .select_from(Cuota)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(
                    Prestamo.estado == "APROBADO",
                    Cuota.fecha_vencimiento < inicio_d,
                    Cuota.fecha_pago >= inicio_d,
                    Cuota.fecha_pago <= fin_d,
                    Cuota.fecha_pago.isnot(None),
                )
            ) or 0

            prog_f = _safe_float(programadas)
            conc_f = _safe_float(conciliados_mes)
            atras_f = _safe_float(pagos_meses_anteriores)
            series.append({
                "mes": m["mes"],
                "cuotas_programadas": prog_f,
                "total_cobrado": conc_f + atras_f,
                "conciliados_mes": conc_f,
                "pagos_meses_anteriores": atras_f,
            })
        origen = "bd"
    except Exception as e:
        logger.exception("Error en tendencia_programado_vs_total_cobrado: %s", e)
        series = [
            {
                "mes": mm["mes"],
                "cuotas_programadas": 0.0,
                "total_cobrado": 0.0,
                "conciliados_mes": 0.0,
                "pagos_meses_anteriores": 0.0,
            }
            for mm in meses
        ]
        origen = "bd"

    return {
        "series": series,
        "origen": origen,
    }


@router.get("/admin")
def get_dashboard_admin(
    periodo: Optional[str] = Query(None),
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Dashboard admin: evolucion_mensual desde tabla cuotas. Con caché 2 veces/día (1:00, 13:00) cuando no se envían fechas."""
    use_cache = not (fecha_inicio and fecha_fin)
    if use_cache:
        with _lock:
            cached = _DASHBOARD_ADMIN_CACHE["data"]
            refreshed = _DASHBOARD_ADMIN_CACHE.get("refreshed_at")
        if cached is not None and refreshed is not None:
            now = datetime.now()
            next_refresh = _next_refresh_local()
            if now < next_refresh:
                return cached
        data = _compute_dashboard_admin(db, fecha_inicio, fecha_fin)
        with _lock:
            _DASHBOARD_ADMIN_CACHE["data"] = data
            _DASHBOARD_ADMIN_CACHE["refreshed_at"] = datetime.now()
        return data
    return _compute_dashboard_admin(db, fecha_inicio, fecha_fin)


@router.get("/analisis-cuentas-por-cobrar")
def get_analisis_cuentas_por_cobrar(
    periodo: Optional[str] = Query(None),
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Análisis de cuentas por cobrar: cartera vs pagos de atrasos por mes."""
    return _compute_analisis_cuentas_por_cobrar(db, fecha_inicio, fecha_fin)


@router.get("/tendencia-programado-total-cobrado")
def get_tendencia_programado_total_cobrado(
    periodo: Optional[str] = Query(None),
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Tendencia mensual: cuotas programadas vs total cobrado (conciliados del mes + pagos de meses anteriores)."""
    return _compute_tendencia_programado_vs_total_cobrado(db, fecha_inicio, fecha_fin)
