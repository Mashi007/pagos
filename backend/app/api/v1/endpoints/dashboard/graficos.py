"""
Dashboard gráficos: cobranzas-semanales, composicion-morosidad, morosidad-analista,
cuentas-cobrar-tendencias, y demás endpoints de gráficos.

Criterios de fecha en prestamos: los graficos que agrupan por tiempo de operacion
suelen filtrar con `prestamo_fecha_referencia_negocio` (base de calculo primero,
luego dia de aprobacion, luego requerimiento), coherente con cuotas ya generadas.
Para vistas explicitamente por mes de aprobacion use la variante
`prestamo_fecha_referencia_por_aprobacion` del modulo de consulta.
"""
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Date, Float, and_, case, cast, distinct, exists, extract, func, literal, literal_column, or_, select
from sqlalchemy.orm import Session, aliased

from app.core.database import get_db, SessionLocal
from app.core.deps import get_current_user
from app.models.cliente import Cliente
from app.models.envio_notificacion import EnvioNotificacion
from app.models.cuota import Cuota
from app.models.modelo_vehiculo import ModeloVehiculo
from app.models.pago import Pago
from app.models.pago_reportado import PagoReportado
from app.models.prestamo import Prestamo
from app.models.tasa_cambio_diaria import TasaCambioDiaria
from app.services.prestamos.prestamo_fecha_referencia_query import (
    prestamo_fecha_referencia_negocio,
)
from app.services.cuota_estado import (
    SQL_PG_ESTADO_CUOTA_CASE_CORRELATED_TOTAL_PAGADO,
    TZ_NEGOCIO,
    hoy_negocio,
)

from .utils import (
    _CACHE_COBRANZAS_SEMANALES,
    _CACHE_COMPOSICION_MOROSIDAD,
    _CACHE_FINANCIAMIENTO_RANGOS,
    _CACHE_MOROSIDAD_ANALISTA,
    _CACHE_MOROSIDAD_DIA,
    _CACHE_PRESTAMOS_POR_CONCESIONARIO,
    _CACHE_PRESTAMOS_POR_MODELO,
    _lock,
    _modelo_label_dashboard_expr,
    _next_refresh_local,
    _prestamos_graficos_cache_key,
    _prestamos_graficos_store,
    _prestamos_graficos_try_hit,
    _safe_float,
    _sanitize_filter_string,
    _etiquetas_12_meses,
    _fechas_iso_desde_periodo_dashboard,
    _meses_desde_rango,
    _ultimo_dia_del_mes,
    _parse_fechas_concesionario,
    _rangos_financiamiento,
)

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])


def _compute_morosidad_por_dia(
    db: Session,
    fecha_inicio: Optional[str],
    fecha_fin: Optional[str],
    dias: Optional[int],
) -> dict:
    """Calcula pago vencido por día: una sola consulta GROUP BY fecha_vencimiento (evita N consultas)."""
    try:
        hoy_utc = datetime.now(timezone.utc)
        hoy_date = date(hoy_utc.year, hoy_utc.month, hoy_utc.day)
        fin = hoy_date
        dias_efectivos = min(90, max(7, dias or 30))
        inicio = fin - timedelta(days=dias_efectivos)
        nombres_mes = ("Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic")

        # Una sola consulta: suma por fecha_vencimiento (solo vencidas y no pagadas)
        q = (
            select(Cuota.fecha_vencimiento, func.coalesce(func.sum(Cuota.monto), 0).label("monto"))
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(
                Prestamo.estado == "APROBADO",
                Cuota.fecha_vencimiento >= inicio,
                Cuota.fecha_vencimiento <= fin,
                Cuota.fecha_vencimiento < hoy_date,
                Cuota.fecha_pago.is_(None),
            )
            .group_by(Cuota.fecha_vencimiento)
        )
        rows = db.execute(q).all()
        morosidad_por_fecha = {r[0]: _safe_float(r[1]) for r in rows}

        resultado = []
        d = inicio
        while d <= fin:
            morosidad_dia = morosidad_por_fecha.get(d, 0.0) if d < hoy_date else 0.0
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


def _compute_financiamiento_por_rangos(
    db: Session,
    fecha_inicio: Optional[str],
    fecha_fin: Optional[str],
    analista: Optional[str],
    concesionario: Optional[str],
    modelo: Optional[str],
) -> dict:
    """Calcula financiamiento por rangos: una sola consulta con CASE (evita 8 consultas)."""
    try:
        conds_base = [
            Prestamo.cliente_id == Cliente.id,
            Prestamo.estado == "APROBADO",
            Prestamo.total_financiamiento.isnot(None),
        ]
        if analista:
            conds_base.append(Prestamo.analista == analista)
        if concesionario:
            conds_base.append(Prestamo.concesionario == concesionario)
        if modelo:
            conds_base.append(Prestamo.modelo_vehiculo == modelo)
        if fecha_inicio and fecha_fin:
            try:
                inicio = date.fromisoformat(fecha_inicio)
                fin = date.fromisoformat(fecha_fin)
                fref = prestamo_fecha_referencia_negocio()
                conds_base.append(fref >= inicio)
                conds_base.append(fref <= fin)
            except ValueError:
                pass

        rangos_def = _rangos_financiamiento()
        # Una consulta: cuenta por rango con CASE (rango 0..5, bandas de $400)
        tf = Prestamo.total_financiamiento
        case_rango = case(
            (tf < 400, 0),
            (tf < 800, 1),
            (tf < 1200, 2),
            (tf < 1600, 3),
            (tf < 2000, 4),
            else_=5,
        )
        q = (
            select(case_rango.label("rango_idx"), func.count().label("n"))
            .select_from(Prestamo)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(and_(*conds_base))
            .group_by(case_rango)
        )
        rows = db.execute(q).all()
        counts_by_idx = {int(r[0]): int(r[1]) for r in rows}
        resultado = []
        total_p = 0
        for idx, (min_val, max_val, cat) in enumerate(rangos_def):
            n = counts_by_idx.get(idx, 0)
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
            ("$0 - $400", 0),
            ("$400 - $800", 0),
            ("$800 - $1,200", 0),
            ("$1,200 - $1,600", 0),
            ("$1,600 - $2,000", 0),
            ("Más de $2,000", 0),
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


def _compute_composicion_morosidad(
    db: Session,
    fecha_inicio: Optional[str],
    fecha_fin: Optional[str],
    analista: Optional[str],
    concesionario: Optional[str],
    modelo: Optional[str],
) -> dict:
    """
    Por prestamo: la ultima cuota de la tabla de amortizacion (mayor numero_cuota)
    define el estado del prestamo. Misma regla que `estado` en GET /prestamos/{id}/cuotas
    (America/Caracas): PAGADO, PAGO_ADELANTADO, PENDIENTE, PARCIAL, VENCIDO, MORA.

    Agrupacion del grafico: Pagado (PAGADO + PAGO_ADELANTADO), Pendiente, Pendiente parcial,
    Vencido, Mora (4 meses+).
    """
    try:
        mx = (
            select(Cuota.prestamo_id, func.max(Cuota.numero_cuota).label("max_n"))
            .group_by(Cuota.prestamo_id)
        ).subquery()

        c = aliased(Cuota, name="c")

        estado_expr = literal_column(
            "(" + SQL_PG_ESTADO_CUOTA_CASE_CORRELATED_TOTAL_PAGADO + ")"
        )

        conds_prestamo = [Prestamo.estado == "APROBADO"]
        if analista:
            conds_prestamo.append(Prestamo.analista == analista)
        if concesionario:
            conds_prestamo.append(Prestamo.concesionario == concesionario)
        if modelo:
            conds_prestamo.append(Prestamo.modelo_vehiculo == modelo)
        if fecha_inicio and fecha_fin:
            try:
                inicio = date.fromisoformat(fecha_inicio)
                fin = date.fromisoformat(fecha_fin)
                fref = prestamo_fecha_referencia_negocio()
                conds_prestamo.append(fref >= inicio)
                conds_prestamo.append(fref <= fin)
            except ValueError:
                pass

        q = (
            select(
                estado_expr.label("estado"),
                func.count().label("n"),
                func.coalesce(func.sum(c.monto), 0).label("monto"),
            )
            .select_from(c)
            .join(
                mx,
                and_(c.prestamo_id == mx.c.prestamo_id, c.numero_cuota == mx.c.max_n),
            )
            .join(Prestamo, c.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(and_(*conds_prestamo))
            .group_by(estado_expr)
        )
        rows = db.execute(q).all()

        merged: dict[str, dict] = {}
        for estado, n, monto in rows:
            code = (estado or "").strip().upper()
            if code in ("PAGADO", "PAGO_ADELANTADO"):
                cat = "Pagado"
            elif code == "PENDIENTE":
                cat = "Pendiente"
            elif code == "PARCIAL":
                cat = "Pendiente parcial"
            elif code == "VENCIDO":
                cat = "Vencido"
            elif code == "MORA":
                cat = "Mora (4 meses+)"
            else:
                cat = code or "Otro"
            if cat not in merged:
                merged[cat] = {"n": 0, "m": 0.0}
            merged[cat]["n"] += int(n)
            merged[cat]["m"] += float(_safe_float(monto))

        orden = (
            "Pagado",
            "Pendiente",
            "Pendiente parcial",
            "Vencido",
            "Mora (4 meses+)",
        )
        puntos = []
        total_monto = 0.0
        total_cuotas = 0
        total_prestamos = 0
        for cat in orden:
            data = merged.get(cat, {"n": 0, "m": 0.0})
            n = int(data["n"])
            m = float(data["m"])
            total_prestamos += n
            total_monto += m
            total_cuotas += n
            puntos.append(
                {
                    "categoria": cat,
                    "monto": m,
                    "cantidad_cuotas": n,
                    "cantidad_prestamos": n,
                }
            )
        if merged.get("Otro", {}).get("n", 0):
            o = merged["Otro"]
            puntos.append(
                {
                    "categoria": "Otro",
                    "monto": float(o["m"]),
                    "cantidad_cuotas": int(o["n"]),
                    "cantidad_prestamos": int(o["n"]),
                }
            )
            total_prestamos += int(o["n"])
            total_monto += float(o["m"])
            total_cuotas += int(o["n"])

        return {
            "puntos": puntos,
            "total_morosidad": total_monto,
            "total_cuotas": total_cuotas,
            "total_prestamos": total_prestamos,
        }
    except Exception as e:
        logger.exception("Error en composicion-morosidad: %s", e)
        return {
            "puntos": [],
            "total_morosidad": 0.0,
            "total_cuotas": 0,
            "total_prestamos": 0,
        }


def _compute_cobranzas_semanales(
    db: Session,
    fecha_inicio: Optional[str],
    fecha_fin: Optional[str],
    semanas: Optional[int],
    analista: Optional[str],
    concesionario: Optional[str],
    modelo: Optional[str],
) -> dict:
    """Calcula cobranzas semanales."""
    try:
        hoy = date.today()
        sem = []
        for i in range(min(semanas or 12, 12)):
            fin_semana = hoy - timedelta(weeks=i)
            inicio_semana = fin_semana - timedelta(days=6)
            pagos_reales = db.scalar(
                select(func.count())
                .select_from(Cuota)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(
                    Prestamo.estado == "APROBADO",
                    Cuota.fecha_pago.isnot(None),
                    func.date(Cuota.fecha_pago) >= inicio_semana,
                    func.date(Cuota.fecha_pago) <= fin_semana,
                )
            ) or 0
            monto_reales = db.scalar(
                select(func.coalesce(func.sum(Cuota.monto), 0))
                .select_from(Cuota)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(
                    Prestamo.estado == "APROBADO",
                    Cuota.fecha_pago.isnot(None),
                    func.date(Cuota.fecha_pago) >= inicio_semana,
                    func.date(Cuota.fecha_pago) <= fin_semana,
                )
            ) or 0
            sem.append({
                "semana_inicio": inicio_semana.isoformat(),
                "nombre_semana": f"Sem {12 - i}",
                "cobranzas_planificadas": 0,
                "pagos_reales": pagos_reales,
                "monto_reales": _safe_float(monto_reales),
            })
        return {"semanas": sem, "fecha_inicio": fecha_inicio or "", "fecha_fin": fecha_fin or ""}
    except Exception as e:
        logger.exception("Error en cobranzas-semanales: %s", e)
        return {"semanas": [], "fecha_inicio": fecha_inicio or "", "fecha_fin": fecha_fin or ""}


def _compute_morosidad_por_analista(
    db: Session,
    fecha_inicio: Optional[str],
    fecha_fin: Optional[str],
    analista: Optional[str],
    concesionario: Optional[str],
    modelo: Optional[str],
) -> dict:
    """Cuotas vencidas por analista."""
    try:
        hoy = date.today()
        conds = [
            Cuota.prestamo_id == Prestamo.id,
            Prestamo.cliente_id == Cliente.id,
            Prestamo.estado == "APROBADO",
            Cuota.fecha_pago.is_(None),
            Cuota.fecha_vencimiento < hoy,
        ]
        if analista:
            conds.append(Prestamo.analista == analista)
        if concesionario:
            conds.append(Prestamo.concesionario == concesionario)
        if modelo:
            conds.append(Prestamo.modelo_vehiculo == modelo)

        analista_label = func.coalesce(Prestamo.analista, "Sin analista")
        q = (
            select(
                analista_label.label("analista"),
                func.count().label("cantidad_cuotas_vencidas"),
                func.coalesce(func.sum(Cuota.monto), 0).label("monto_vencido"),
            )
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(and_(*conds))
            .group_by(analista_label)
        )
        rows = db.execute(q).all()
        resultado = [
            {
                "analista": str(r[0]) if r[0] else "Sin analista",
                "cantidad_cuotas_vencidas": int(r[1]),
                "monto_vencido": round(_safe_float(r[2]), 2),
            }
            for r in rows
        ]
        resultado.sort(key=lambda x: -x["monto_vencido"])
        return {"analistas": resultado}
    except Exception as e:
        logger.exception("Error en morosidad-por-analista: %s", e)
        try:
            db.rollback()
        except Exception:
            pass
        return {"analistas": []}


# ========== Endpoints ==========

@router.get("/financiamiento-tendencia-mensual")
def get_financiamiento_tendencia_mensual(
    fecha_inicio: Optional[str] = Query(None),
    meses: Optional[int] = Query(12, ge=1, le=24),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Tendencia mensual de financiamiento."""
    analista = _sanitize_filter_string(analista)
    concesionario = _sanitize_filter_string(concesionario)
    modelo = _sanitize_filter_string(modelo)
    try:
        meses_list = _etiquetas_12_meses()
        hoy = datetime.now(timezone.utc)
        resultado = []
        for i, m in enumerate(meses_list):
            fin_mes = hoy - timedelta(days=30 * (11 - i))
            ultimo_dia = _ultimo_dia_del_mes(fin_mes.replace(tzinfo=timezone.utc) if fin_mes.tzinfo is None else fin_mes)
            ultimo_d = ultimo_dia.date() if hasattr(ultimo_dia, "date") else ultimo_dia
            cartera = db.scalar(
                select(func.coalesce(func.sum(Prestamo.total_financiamiento), 0))
                .select_from(Prestamo)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(prestamo_fecha_referencia_negocio() <= ultimo_d, Prestamo.estado == "APROBADO")
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
        return {"meses": _etiquetas_12_meses()}


@router.get("/morosidad-por-dia")
def get_morosidad_por_dia(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    dias: Optional[int] = Query(30, ge=7, le=90),
    db: Session = Depends(get_db),
):
    """Morosidad por día. Con caché 2 veces/día (1:00, 13:00) cuando no se envían fechas."""
    use_cache = not (fecha_inicio and fecha_fin)
    if use_cache:
        with _lock:
            cached = _CACHE_MOROSIDAD_DIA["data"]
            refreshed = _CACHE_MOROSIDAD_DIA.get("refreshed_at")
        if cached is not None and refreshed is not None and datetime.now() < _next_refresh_local():
            return cached
    data = _compute_morosidad_por_dia(db, fecha_inicio, fecha_fin, dias)
    if use_cache:
        with _lock:
            _CACHE_MOROSIDAD_DIA["data"] = data
            _CACHE_MOROSIDAD_DIA["refreshed_at"] = datetime.now()
    return data


@router.get("/proyeccion-cobro-30-dias")
def get_proyeccion_cobro_30_dias(db: Session = Depends(get_db)):
    """Proyección de cobro: monto programado por día desde hoy hasta hoy+30."""
    try:
        hoy_utc = datetime.now(timezone.utc)
        hoy_date = date(hoy_utc.year, hoy_utc.month, hoy_utc.day)
        fin_date = hoy_date + timedelta(days=30)
        resultado = []
        nombres_mes = ("Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic")
        d = hoy_date
        while d <= fin_date:
            programado = db.scalar(
                select(func.coalesce(func.sum(Cuota.monto), 0))
                .select_from(Cuota)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(Prestamo.estado == "APROBADO", Cuota.fecha_vencimiento == d)
            ) or 0
            pendiente = db.scalar(
                select(func.coalesce(func.sum(Cuota.monto), 0))
                .select_from(Cuota)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(Prestamo.estado == "APROBADO", Cuota.fecha_vencimiento == d, Cuota.fecha_pago.is_(None))
            ) or 0
            resultado.append({
                "fecha": d.isoformat(),
                "dia": f"{d.day} {nombres_mes[d.month - 1]}",
                "monto_programado": round(_safe_float(programado), 2),
                "monto_pendiente": round(_safe_float(pendiente), 2),
            })
            d += timedelta(days=1)
        return {"dias": resultado}
    except Exception as e:
        logger.exception("Error en proyeccion-cobro-30-dias: %s", e)
        return {"dias": []}


@router.get("/monto-programado-proxima-semana")
def get_monto_programado_proxima_semana(db: Session = Depends(get_db)):
    """Monto programado por día: vencimientos entre hoy+4 y hoy+7 (4 días en el futuro)."""
    try:
        hoy_utc = datetime.now(timezone.utc)
        hoy_date = date(hoy_utc.year, hoy_utc.month, hoy_utc.day)
        inicio_date = hoy_date + timedelta(days=4)
        fin_date = hoy_date + timedelta(days=7)
        resultado = []
        nombres_mes = ("Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic")
        d = inicio_date
        while d <= fin_date:
            programado = db.scalar(
                select(func.coalesce(func.sum(Cuota.monto), 0))
                .select_from(Cuota)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(Prestamo.estado == "APROBADO", Cuota.fecha_vencimiento == d)
            ) or 0
            resultado.append({
                "fecha": d.isoformat(),
                "dia": f"{d.day} {nombres_mes[d.month - 1]}",
                "monto_programado": round(_safe_float(programado), 2),
            })
            d += timedelta(days=1)
        return {"dias": resultado}
    except Exception as e:
        logger.exception("Error en monto-programado-proxima-semana: %s", e)
        return {"dias": []}


def _compute_prestamos_por_concesionario(
    db: Session,
    fecha_inicio: Optional[str],
    fecha_fin: Optional[str],
    analista: Optional[str],
    concesionario: Optional[str],
    modelo: Optional[str],
) -> dict:
    """Agregados préstamos por concesionario (sin caché)."""
    try:
        inicio, fin = _parse_fechas_concesionario(fecha_inicio, fecha_fin)
        fref = prestamo_fecha_referencia_negocio()
        mes_expr = func.to_char(func.date_trunc("month", fref), "YYYY-MM")
        concesionario_label = func.coalesce(Prestamo.concesionario, "Sin concesionario").label("concesionario")
        conds_base = [
            Prestamo.estado == "APROBADO",
            fref >= inicio,
            fref <= fin,
        ]
        if analista:
            conds_base.append(Prestamo.analista == analista)
        if concesionario:
            conds_base.append(Prestamo.concesionario == concesionario)
        if modelo:
            conds_base.append(Prestamo.modelo_vehiculo == modelo)
        q_por_mes = (
            select(mes_expr.label("mes"), concesionario_label, func.count().label("cantidad"))
            .select_from(Prestamo)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(and_(*conds_base))
            .group_by(mes_expr, Prestamo.concesionario)
            .order_by(mes_expr, func.count().desc())
        )
        rows_por_mes = db.execute(q_por_mes).all()
        por_mes = [{"mes": r.mes, "concesionario": r.concesionario, "cantidad": r.cantidad} for r in rows_por_mes]
        conds_acum = [Prestamo.estado == "APROBADO"]
        if analista:
            conds_acum.append(Prestamo.analista == analista)
        if concesionario:
            conds_acum.append(Prestamo.concesionario == concesionario)
        if modelo:
            conds_acum.append(Prestamo.modelo_vehiculo == modelo)
        q_acum = (
            select(func.coalesce(Prestamo.concesionario, "Sin concesionario").label("concesionario"), func.count().label("cantidad_acumulada"))
            .select_from(Prestamo)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(and_(*conds_acum))
            .group_by(Prestamo.concesionario)
            .order_by(func.count().desc())
        )
        rows_acum = db.execute(q_acum).all()
        acumulado = [{"concesionario": r.concesionario, "cantidad_acumulada": r.cantidad_acumulada} for r in rows_acum]
        return {"por_mes": por_mes, "acumulado": acumulado}
    except Exception as e:
        logger.exception("Error en prestamos-por-concesionario: %s", e)
        return {"por_mes": [], "acumulado": []}


def _compute_prestamos_por_modelo(
    db: Session,
    fecha_inicio: Optional[str],
    fecha_fin: Optional[str],
    analista: Optional[str],
    concesionario: Optional[str],
    modelo_filtro: Optional[str],
) -> dict:
    """Agregados préstamos por modelo (sin caché)."""
    try:
        inicio, fin = _parse_fechas_concesionario(fecha_inicio, fecha_fin)
        fref = prestamo_fecha_referencia_negocio()
        mes_expr = func.to_char(func.date_trunc("month", fref), "YYYY-MM")
        producto_valido = func.nullif(func.nullif(func.trim(Prestamo.producto), ""), "Financiamiento")
        modelo_expr = _modelo_label_dashboard_expr(
            producto_valido,
            incluir_sin_modelo=True,
        )
        conds_base = [
            Prestamo.estado == "APROBADO",
            fref >= inicio,
            fref <= fin,
        ]
        if analista:
            conds_base.append(Prestamo.analista == analista)
        if concesionario:
            conds_base.append(Prestamo.concesionario == concesionario)
        if modelo_filtro:
            conds_base.append(or_(
                Prestamo.modelo_vehiculo == modelo_filtro,
                ModeloVehiculo.modelo == modelo_filtro,
                Prestamo.producto == modelo_filtro,
            ))
        q_por_mes = (
            select(mes_expr.label("mes"), modelo_expr.label("modelo"), func.count().label("cantidad"))
            .select_from(Prestamo)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .outerjoin(ModeloVehiculo, Prestamo.modelo_vehiculo_id == ModeloVehiculo.id)
            .where(and_(*conds_base))
            .group_by(mes_expr, modelo_expr)
            .order_by(mes_expr, func.count().desc())
        )
        rows_por_mes = db.execute(q_por_mes).all()
        por_mes = [{"mes": r.mes, "modelo": r.modelo or "Sin modelo", "cantidad": r.cantidad} for r in rows_por_mes]
        q_acum = (
            select(modelo_expr.label("modelo"), func.count().label("cantidad_acumulada"))
            .select_from(Prestamo)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .outerjoin(ModeloVehiculo, Prestamo.modelo_vehiculo_id == ModeloVehiculo.id)
            .where(and_(*conds_base))
            .group_by(modelo_expr)
            .order_by(func.count().desc())
        )
        rows_acum = db.execute(q_acum).all()
        acumulado = [{"modelo": r.modelo or "Sin modelo", "cantidad_acumulada": r.cantidad_acumulada} for r in rows_acum]
        return {"por_mes": por_mes, "acumulado": acumulado}
    except Exception as e:
        logger.exception("Error en prestamos-por-modelo: %s", e)
        return {"por_mes": [], "acumulado": []}


@router.get("/prestamos-por-concesionario")
def get_prestamos_por_concesionario(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Préstamos aprobados por concesionario. Caché en memoria 5 min por misma consulta."""
    analista = _sanitize_filter_string(analista)
    concesionario = _sanitize_filter_string(concesionario)
    modelo = _sanitize_filter_string(modelo)
    ck = _prestamos_graficos_cache_key(fecha_inicio, fecha_fin, analista, concesionario, modelo)
    hit = _prestamos_graficos_try_hit(_CACHE_PRESTAMOS_POR_CONCESIONARIO, ck)
    if hit is not None:
        return hit
    data = _compute_prestamos_por_concesionario(db, fecha_inicio, fecha_fin, analista, concesionario, modelo)
    _prestamos_graficos_store(_CACHE_PRESTAMOS_POR_CONCESIONARIO, ck, data)
    return data


@router.get("/prestamos-por-modelo")
def get_prestamos_por_modelo(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Préstamos aprobados por modelo. Caché en memoria 5 min por misma consulta."""
    analista = _sanitize_filter_string(analista)
    concesionario = _sanitize_filter_string(concesionario)
    modelo_filtro = _sanitize_filter_string(modelo)
    ck = _prestamos_graficos_cache_key(fecha_inicio, fecha_fin, analista, concesionario, modelo_filtro)
    hit = _prestamos_graficos_try_hit(_CACHE_PRESTAMOS_POR_MODELO, ck)
    if hit is not None:
        return hit
    data = _compute_prestamos_por_modelo(db, fecha_inicio, fecha_fin, analista, concesionario, modelo_filtro)
    _prestamos_graficos_store(_CACHE_PRESTAMOS_POR_MODELO, ck, data)
    return data


@router.get("/financiamiento-por-rangos")
def get_financiamiento_por_rangos(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Bandas por total_financiamiento. Con caché 2 veces/día (1:00, 13:00) cuando no se envían filtros."""
    analista = _sanitize_filter_string(analista)
    concesionario = _sanitize_filter_string(concesionario)
    modelo = _sanitize_filter_string(modelo)
    use_cache = not (fecha_inicio or fecha_fin or analista or concesionario or modelo)
    if use_cache:
        with _lock:
            cached = _CACHE_FINANCIAMIENTO_RANGOS["data"]
            refreshed = _CACHE_FINANCIAMIENTO_RANGOS.get("refreshed_at")
        if cached is not None and refreshed is not None and datetime.now() < _next_refresh_local():
            return cached
    data = _compute_financiamiento_por_rangos(db, fecha_inicio, fecha_fin, analista, concesionario, modelo)
    if use_cache:
        with _lock:
            _CACHE_FINANCIAMIENTO_RANGOS["data"] = data
            _CACHE_FINANCIAMIENTO_RANGOS["refreshed_at"] = datetime.now()
    return data


@router.get("/composicion-morosidad")
def get_composicion_morosidad(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Composición de morosidad. Con caché 2 veces/día (1:00, 13:00) cuando no se envían filtros."""
    analista = _sanitize_filter_string(analista)
    concesionario = _sanitize_filter_string(concesionario)
    modelo = _sanitize_filter_string(modelo)
    use_cache = not (fecha_inicio or fecha_fin or analista or concesionario or modelo)
    if use_cache:
        with _lock:
            cached = _CACHE_COMPOSICION_MOROSIDAD["data"]
            refreshed = _CACHE_COMPOSICION_MOROSIDAD.get("refreshed_at")
        if cached is not None and refreshed is not None and datetime.now() < _next_refresh_local():
            return cached
    data = _compute_composicion_morosidad(db, fecha_inicio, fecha_fin, analista, concesionario, modelo)
    if use_cache:
        with _lock:
            _CACHE_COMPOSICION_MOROSIDAD["data"] = data
            _CACHE_COMPOSICION_MOROSIDAD["refreshed_at"] = datetime.now()
    return data


@router.get("/cobranza-fechas-especificas", summary="[Stub] Requiere tabla pagos/cobranzas para datos reales.")
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


@router.get("/cobranzas-semanales", summary="Cobranzas semanales desde BD (Cuota/Prestamo).")
def get_cobranzas_semanales(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    semanas: Optional[int] = Query(12, ge=1, le=52),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Cobranzas semanales. Con caché 2 veces/día (1:00, 13:00) cuando no se envían filtros."""
    analista = _sanitize_filter_string(analista)
    concesionario = _sanitize_filter_string(concesionario)
    modelo = _sanitize_filter_string(modelo)
    use_cache = not (fecha_inicio or fecha_fin or analista or concesionario or modelo)
    if use_cache:
        with _lock:
            cached = _CACHE_COBRANZAS_SEMANALES["data"]
            refreshed = _CACHE_COBRANZAS_SEMANALES.get("refreshed_at")
        if cached is not None and refreshed is not None and datetime.now() < _next_refresh_local():
            return cached
    data = _compute_cobranzas_semanales(db, fecha_inicio, fecha_fin, semanas, analista, concesionario, modelo)
    if use_cache:
        with _lock:
            _CACHE_COBRANZAS_SEMANALES["data"] = data
            _CACHE_COBRANZAS_SEMANALES["refreshed_at"] = datetime.now()
    return data


@router.get("/morosidad-por-analista")
def get_morosidad_por_analista(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Morosidad por analista. Con caché 2 veces/día (1:00, 13:00) cuando no se envían filtros."""
    analista = _sanitize_filter_string(analista)
    concesionario = _sanitize_filter_string(concesionario)
    modelo = _sanitize_filter_string(modelo)
    use_cache = not (fecha_inicio or fecha_fin or analista or concesionario or modelo)
    if use_cache:
        with _lock:
            cached = _CACHE_MOROSIDAD_ANALISTA["data"]
            refreshed = _CACHE_MOROSIDAD_ANALISTA.get("refreshed_at")
        if cached is not None and refreshed is not None and datetime.now() < _next_refresh_local():
            return cached
    data = _compute_morosidad_por_analista(db, fecha_inicio, fecha_fin, analista, concesionario, modelo)
    if use_cache:
        with _lock:
            _CACHE_MOROSIDAD_ANALISTA["data"] = data
            _CACHE_MOROSIDAD_ANALISTA["refreshed_at"] = datetime.now()
    return data


@router.get("/evolucion-morosidad")
def get_evolucion_morosidad(
    fecha_inicio: Optional[str] = Query(None),
    meses: Optional[int] = Query(12, ge=1, le=24),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Evolución de morosidad por mes."""
    analista = _sanitize_filter_string(analista)
    concesionario = _sanitize_filter_string(concesionario)
    modelo = _sanitize_filter_string(modelo)
    try:
        meses_list = _etiquetas_12_meses()
        hoy = datetime.now(timezone.utc)
        resultado = []
        hoy_date = hoy.date() if hasattr(hoy, "date") else date(hoy.year, hoy.month, hoy.day)
        for i, m in enumerate(meses_list):
            fin_mes = hoy - timedelta(days=30 * (11 - i))
            ultimo_dia = _ultimo_dia_del_mes(fin_mes.replace(tzinfo=timezone.utc) if fin_mes.tzinfo is None else fin_mes)
            ultimo_dia_date = ultimo_dia.date() if hasattr(ultimo_dia, "date") else ultimo_dia
            ref = min(ultimo_dia_date, hoy_date)
            moro = db.scalar(
                select(func.coalesce(func.sum(Cuota.monto), 0))
                .select_from(Cuota)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(
                    Prestamo.estado == "APROBADO",
                    Cuota.fecha_pago.is_(None),
                    Cuota.fecha_vencimiento < ref,
                )
            ) or 0
            resultado.append({"mes": m["mes"], "morosidad": _safe_float(moro)})
        return {"meses": resultado}
    except Exception as e:
        logger.exception("Error en evolucion-morosidad: %s", e)
        m = _etiquetas_12_meses()
        return {"meses": [{"mes": x["mes"], "morosidad": x["morosidad"]} for x in m]}


@router.get("/evolucion-pagos", summary="Evolución de pagos por mes desde BD (Cuota.fecha_pago).")
def get_evolucion_pagos(
    fecha_inicio: Optional[str] = Query(None),
    meses: Optional[int] = Query(12, ge=1, le=24),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Evolución de pagos por mes."""
    analista = _sanitize_filter_string(analista)
    concesionario = _sanitize_filter_string(concesionario)
    modelo = _sanitize_filter_string(modelo)
    try:
        meses_list = _etiquetas_12_meses()
        hoy = datetime.now(timezone.utc)
        resultado = []
        for i, m in enumerate(meses_list):
            fin_mes = hoy - timedelta(days=30 * (11 - i))
            ultimo_dia = _ultimo_dia_del_mes(fin_mes.replace(tzinfo=timezone.utc) if fin_mes.tzinfo is None else fin_mes)
            ultimo_dia_date = ultimo_dia.date() if hasattr(ultimo_dia, "date") else ultimo_dia
            inicio_mes = ultimo_dia_date.replace(day=1)
            pagos_count = db.scalar(
                select(func.count())
                .select_from(Cuota)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(
                    Prestamo.estado == "APROBADO",
                    Cuota.fecha_pago.isnot(None),
                    func.date(Cuota.fecha_pago) >= inicio_mes,
                    func.date(Cuota.fecha_pago) <= ultimo_dia_date,
                )
            ) or 0
            monto_pagado = db.scalar(
                select(func.coalesce(func.sum(Cuota.monto), 0))
                .select_from(Cuota)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(
                    Prestamo.estado == "APROBADO",
                    Cuota.fecha_pago.isnot(None),
                    func.date(Cuota.fecha_pago) >= inicio_mes,
                    func.date(Cuota.fecha_pago) <= ultimo_dia_date,
                )
            ) or 0
            resultado.append({"mes": m["mes"], "pagos": pagos_count, "monto": _safe_float(monto_pagado)})
        return {"meses": resultado}
    except Exception as e:
        logger.exception("Error en evolucion-pagos: %s", e)
        m = _etiquetas_12_meses()
        return {"meses": [{"mes": x["mes"], "pagos": x.get("pagos", 0), "monto": x.get("monto", 0)} for x in m]}


def _trim_serie_bs_recibos_extremos(series: list[dict]) -> list[dict]:
    """
    Quita meses sin movimiento al inicio y al final (bs_en_usd en cero y cantidad 0).
    """
    if not series:
        return []

    def tiene_movimiento(p: dict) -> bool:
        b = _safe_float(p.get("bs_en_usd"))
        c = int(p.get("cantidad") or 0)
        return b > 0 or c > 0

    first = next((i for i, row in enumerate(series) if tiene_movimiento(row)), None)
    if first is None:
        return []
    last = next(
        (i for i in range(len(series) - 1, -1, -1) if tiene_movimiento(series[i])),
        first,
    )
    return series[first : last + 1]


def _estadistica_recibos_bs_usd(series: list[dict]) -> dict:
    """Totales y promedios sobre la serie ya recortada (solo meses con datos visibles)."""
    if not series:
        return {
            "total_bs_en_usd": 0.0,
            "total_reportes": 0,
            "promedio_mensual_usd": 0.0,
            "meses_con_datos": 0,
            "primer_mes": None,
            "ultimo_mes": None,
        }
    total_usd = sum(_safe_float(p.get("bs_en_usd")) for p in series)
    total_rep = sum(int(p.get("cantidad") or 0) for p in series)
    n = len(series)
    return {
        "total_bs_en_usd": round(total_usd, 2),
        "total_reportes": total_rep,
        "promedio_mensual_usd": round(total_usd / n, 2) if n else 0.0,
        "meses_con_datos": n,
        "primer_mes": series[0].get("mes"),
        "ultimo_mes": series[-1].get("mes"),
    }


def _compute_recibos_pagos_mensual_usd(
    db: Session,
    fecha_inicio: Optional[str],
    fecha_fin: Optional[str],
) -> dict:
    """
    Solo reportes en bolívares (moneda BS) con recibo: equivalente USD por mes.
    Conversión: monto en tabla pagos si existe (enlace por COB-RPC legacy, numero_operacion o RPC en documento);
    si no, monto BS / tasa oficial del día.
    Serie recortada sin meses vacíos al inicio/fin; incluye estadística agregada.
    """
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

    min_date: Optional[date] = None
    max_date: Optional[date] = None
    for m in meses:
        y, mo = m["year"], m["month"]
        id_ = date(y, mo, 1)
        fd_ = date(y, 12, 31) if mo == 12 else date(y, mo + 1, 1) - timedelta(days=1)
        min_date = id_ if min_date is None or id_ < min_date else min_date
        max_date = fd_ if max_date is None or fd_ > max_date else max_date

    buckets: dict[tuple[int, int], dict[str, float]] = {}
    try:
        # Agregación en BD: evita transferir N filas + IN masivo a pagos (timeout ~60s en Render).
        # Enlace pagos ↔ reportado: legacy COB-RPC, operación bancaria, o RPC solo (sin subir duplicados por OR en JOIN).
        P_doc = aliased(Pago)
        doc_cob = func.substr(
            func.concat("COB-", func.coalesce(PagoReportado.referencia_interna, "")),
            1,
            100,
        )
        op_trim = func.nullif(func.trim(func.coalesce(PagoReportado.numero_operacion, "")), "")
        ref_trim = func.nullif(func.trim(func.coalesce(PagoReportado.referencia_interna, "")), "")
        pago_en_reportado = or_(
            P_doc.numero_documento == doc_cob,
            and_(op_trim.isnot(None), P_doc.numero_documento == op_trim),
            and_(
                op_trim.is_(None),
                ref_trim.isnot(None),
                P_doc.numero_documento == ref_trim,
            ),
        )
        monto_pago_en_usd = (
            select(cast(P_doc.monto_pagado, Float))
            .where(pago_en_reportado)
            .order_by(P_doc.id.desc())
            .limit(1)
            .correlate(PagoReportado)
            .scalar_subquery()
        )
        mon_raw = func.upper(func.trim(func.coalesce(PagoReportado.moneda, "BS")))
        mon_norm = case((mon_raw == "USDT", literal("USD")), else_=mon_raw)

        tasa_ok = and_(
            TasaCambioDiaria.tasa_oficial.isnot(None),
            TasaCambioDiaria.tasa_oficial > 0,
        )
        bs_from_tasa = case(
            (
                tasa_ok,
                cast(PagoReportado.monto, Float) / cast(TasaCambioDiaria.tasa_oficial, Float),
            ),
            else_=literal(0.0),
        )
        bs_en_usd_expr = case(
            (monto_pago_en_usd.isnot(None), monto_pago_en_usd),
            else_=bs_from_tasa,
        )

        yr = extract("year", PagoReportado.fecha_pago)
        mo = extract("month", PagoReportado.fecha_pago)
        tiene_recibo = or_(
            PagoReportado.recibo_pdf.isnot(None),
            and_(
                PagoReportado.ruta_recibo_pdf.isnot(None),
                func.trim(PagoReportado.ruta_recibo_pdf) != "",
            ),
        )
        solo_bs = mon_norm == literal("BS")
        q = (
            select(
                yr.label("anio"),
                mo.label("mes_num"),
                func.coalesce(func.sum(bs_en_usd_expr), 0).label("bs_en_usd"),
                func.count(PagoReportado.id).label("cantidad"),
            )
            .select_from(PagoReportado)
            .outerjoin(TasaCambioDiaria, TasaCambioDiaria.fecha == PagoReportado.fecha_pago)
            .where(
                tiene_recibo,
                solo_bs,
                PagoReportado.estado.in_(("aprobado", "importado")),
                PagoReportado.fecha_pago >= min_date,
                PagoReportado.fecha_pago <= max_date,
            )
            .group_by(yr, mo)
        )

        for row in db.execute(q).all():
            yk, mk = int(row.anio), int(row.mes_num)
            buckets[(yk, mk)] = {
                "bs_en_usd": float(row.bs_en_usd or 0),
                "cantidad": int(row.cantidad or 0),
            }

        series_raw: list[dict] = []
        for m in meses:
            yk, mk = m["year"], m["month"]
            b = buckets.get((yk, mk), {"bs_en_usd": 0.0, "cantidad": 0})
            series_raw.append({
                "mes": m["mes"],
                "bs_en_usd": round(b["bs_en_usd"], 2),
                "cantidad": int(b["cantidad"]),
            })
        series = _trim_serie_bs_recibos_extremos(series_raw)
        estadistica = _estadistica_recibos_bs_usd(series)
        return {"series": series, "estadistica": estadistica, "origen": "bd"}
    except Exception as e:
        logger.exception("Error en recibos-pagos-mensual-usd: %s", e)
        fallback = [
            {"mes": mm["mes"], "bs_en_usd": 0.0, "cantidad": 0}
            for mm in meses
        ]
        series = _trim_serie_bs_recibos_extremos(fallback)
        return {
            "series": series,
            "estadistica": _estadistica_recibos_bs_usd(series),
            "origen": "bd",
        }


@router.get("/recibos-pagos-mensual-usd")
def get_recibos_pagos_mensual_usd(
    periodo: Optional[str] = Query(None),
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Recibos solo en Bs.: equivalente USD por mes (pago conciliado o tasa del día) + estadística."""
    fi, ff = fecha_inicio, fecha_fin
    if not (fi and ff):
        pfi, pff = _fechas_iso_desde_periodo_dashboard(periodo)
        if pfi and pff:
            fi, ff = pfi, pff
    return _compute_recibos_pagos_mensual_usd(db, fi, ff)


@router.get("/cobranza-por-dia", summary="[Stub] Devuelve dias vacíos hasta tener tabla pagos/cobranzas.")
def get_cobranza_por_dia(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Cobranza por día desde BD."""
    return {"dias": []}


@router.get("/cobranzas-mensuales", summary="[Stub] Devuelve meses vacíos hasta tener tabla pagos/cobranzas.")
def get_cobranzas_mensuales(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Cobranzas mensuales desde BD."""
    return {"meses": []}


@router.get("/cobros-por-analista", summary="[Stub] Devuelve analistas vacíos hasta tener tabla pagos.")
def get_cobros_por_analista(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Cobros por analista desde BD."""
    return {"analistas": []}


@router.get("/cobros-diarios", summary="[Stub] Devuelve dias vacíos hasta tener tabla pagos.")
def get_cobros_diarios(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Cobros diarios desde BD."""
    return {"dias": []}


@router.get("/cuentas-cobrar-tendencias", summary="[Stub] Devuelve tendencias vacías hasta tener datos.")
def get_cuentas_cobrar_tendencias(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Tendencias cuentas por cobrar desde BD."""
    return {"tendencias": []}


# Tipo(s) de pestaña permitidos para la tendencia diaria (ampliar cuando se agreguen más series en UI).
TIPOS_NOTIFICACIONES_ENVIOS_TENDENCIA = frozenset({"dias_1_retraso"})


def _compute_notificaciones_envios_por_dia(db: Session, tipo_tab: str, dias: int) -> dict:
    """
    Cuenta envíos registrados en envios_notificacion por día calendario (America/Caracas).
    dias_1_retraso = notificaciones «día siguiente al vencimiento» en la UI.
    """
    try:
        dias_ef = min(366, max(7, int(dias)))
        hoy_c = hoy_negocio()
        inicio = hoy_c - timedelta(days=dias_ef - 1)
        nombres_mes = ("Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic")
        z = ZoneInfo(TZ_NEGOCIO)
        start_local = datetime.combine(inicio, datetime.min.time(), tzinfo=z)
        start_utc_naive = start_local.astimezone(timezone.utc).replace(tzinfo=None)

        bind = db.get_bind()
        dialect = bind.dialect.name if bind is not None else "postgresql"
        fe = EnvioNotificacion.fecha_envio
        if dialect == "postgresql":
            dia_expr = cast(
                func.timezone("America/Caracas", func.timezone("UTC", fe)),
                Date,
            )
        else:
            dia_expr = cast(fe, Date)

        enviados_sum = func.coalesce(
            func.sum(case((EnvioNotificacion.exito.is_(True), 1), else_=0)),
            0,
        )
        fallidos_sum = func.coalesce(
            func.sum(case((EnvioNotificacion.exito.is_(False), 1), else_=0)),
            0,
        )
        stmt = (
            select(
                dia_expr.label("dia"),
                enviados_sum.label("enviados"),
                fallidos_sum.label("fallidos"),
            )
            .where(
                EnvioNotificacion.tipo_tab == tipo_tab,
                EnvioNotificacion.fecha_envio >= start_utc_naive,
            )
            .group_by(dia_expr)
            .order_by(dia_expr)
        )
        rows = db.execute(stmt).all()
        counts: dict[date, tuple[int, int]] = {}
        for row in rows:
            d = row.dia
            if isinstance(d, datetime):
                d = d.date()
            if not isinstance(d, date):
                continue
            counts[d] = (int(row.enviados or 0), int(row.fallidos or 0))

        serie = []
        d = inicio
        while d <= hoy_c:
            ev, fa = counts.get(d, (0, 0))
            serie.append(
                {
                    "fecha": d.isoformat(),
                    "dia": f"{d.day} {nombres_mes[d.month - 1]}",
                    "enviados": ev,
                    "fallidos": fa,
                }
            )
            d += timedelta(days=1)
        return {"tipo_tab": tipo_tab, "serie": serie}
    except Exception as e:
        logger.exception("Error en notificaciones-envios-por-dia: %s", e)
        return {"tipo_tab": tipo_tab, "serie": []}


@router.get("/notificaciones-envios-por-dia")
def get_notificaciones_envios_por_dia(
    tipo_tab: str = Query(
        "dias_1_retraso",
        description="tipo_tab en envíos. Por ahora solo dias_1_retraso (día siguiente al vencimiento).",
    ),
    dias: int = Query(90, ge=7, le=366),
    db: Session = Depends(get_db),
):
    """Tendencia diaria de envíos de notificación (éxito / fallo) desde envios_notificacion."""
    if tipo_tab not in TIPOS_NOTIFICACIONES_ENVIOS_TENDENCIA:
        raise HTTPException(
            status_code=400,
            detail=f"tipo_tab debe ser uno de: {', '.join(sorted(TIPOS_NOTIFICACIONES_ENVIOS_TENDENCIA))}",
        )
    return _compute_notificaciones_envios_por_dia(db, tipo_tab, dias)


@router.get("/distribucion-prestamos", summary="[Stub] Devuelve distribucion vacía hasta tener datos.")
def get_distribucion_prestamos(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Distribución de préstamos desde BD."""
    return {"distribucion": []}


@router.get("/metricas-acumuladas", summary="[Stub] Devuelve metricas vacías hasta tener datos.")
def get_metricas_acumuladas(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Métricas acumuladas desde BD."""
    return {"metricas": []}
