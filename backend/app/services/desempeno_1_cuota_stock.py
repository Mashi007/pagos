"""
Desempeño diario de cartera (independiente de envíos SMTP):

- 1 cuota (dias_10_retraso): atraso 6–59, exactamente 1 cuota atrasada.
- 2 cuotas (prejudicial): atraso ≥60, exactamente 2 cuotas atrasadas (≥60).

Por día (últimos N, Caracas):
1) Inicio día (morosos / stock_00h) — nivel a las 00:00.
2) Fin dia (notificaciones / stock_23h) — del stock de las 00:00, cuántos
   siguen en el segmento a las 23:00 (no se pagaron). No depende de si hubo correo.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Callable, Literal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.cuota_pago import CuotaPago
from app.models.prestamo import Prestamo
from app.services.cuota_estado import TZ_NEGOCIO, hoy_negocio
from app.services.notificacion_service import (
    MAX_DIAS_ATRASO_PARA_LISTADO_10_DIAS,
    MIN_DIAS_ATRASO_PARA_LISTADO_10_DIAS,
    MIN_DIAS_ATRASO_PREJUDICIAL,
    PREJUDICIAL_MAX_CUOTAS_CON_ATRASO_60,
    PREJUDICIAL_MIN_CUOTAS_CON_ATRASO_60,
    TOL_SALDO_CUOTA_NOTIFICACION,
    _prestamo_no_excluido_notif,
)
from app.services.notificaciones_exclusion_desistimiento import sql_cliente_sin_desistimiento

logger = logging.getLogger(__name__)

_NOMBRES_MES = (
    "Ene", "Feb", "Mar", "Abr", "May", "Jun",
    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
)
TIPO_TAB_1_CUOTA = "dias_10_retraso"
TIPO_TAB_2_CUOTAS = "prejudicial"

CasoDesempeno = Literal["1_cuota", "2_cuotas"]


def _as_aware(dt: datetime, z: ZoneInfo) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc).astimezone(z)
    return dt.astimezone(z)


def _paid_at_caracas(
    *,
    fecha_pago: date | None,
    monto: float,
    eventos: list[tuple[datetime, float, bool]],
    z: ZoneInfo,
) -> datetime | None:
    acum = 0.0
    for ts, m, completo in eventos:
        acum += float(m or 0.0)
        if completo or acum + 1e-9 >= float(monto) - TOL_SALDO_CUOTA_NOTIFICACION:
            return ts
    if fecha_pago is not None:
        return datetime.combine(fecha_pago, time(23, 59, 59), tzinfo=z)
    return None


def _stock_1_cuota_at(
    cuotas_meta: list[dict[str, Any]], t_ref: datetime, z: ZoneInfo
) -> set[int]:
    """Prestamos en segmento 1 cuota en el instante t_ref (Caracas)."""
    t_local = _as_aware(t_ref, z)
    d = t_local.date()
    overdue: dict[int, list[int]] = {}
    for c in cuotas_meta:
        fv = c["fv"]
        if fv >= d:
            continue
        dias_atraso = (d - fv).days
        if dias_atraso < 1:
            continue
        paid_at = c["paid_at"]
        if paid_at is not None and paid_at <= t_local:
            continue
        overdue.setdefault(c["prestamo_id"], []).append(dias_atraso)

    out: set[int] = set()
    for pid, dias_list in overdue.items():
        if len(dias_list) != 1:
            continue
        da = dias_list[0]
        if MIN_DIAS_ATRASO_PARA_LISTADO_10_DIAS <= da <= MAX_DIAS_ATRASO_PARA_LISTADO_10_DIAS:
            out.add(pid)
    return out


def _stock_2_cuotas_at(
    cuotas_meta: list[dict[str, Any]], t_ref: datetime, z: ZoneInfo
) -> set[int]:
    """Exactamente 2 cuotas impagas con atraso >= 60 en el instante t_ref."""
    t_local = _as_aware(t_ref, z)
    d = t_local.date()
    counts: dict[int, int] = {}
    for c in cuotas_meta:
        fv = c["fv"]
        if fv >= d:
            continue
        dias_atraso = (d - fv).days
        if dias_atraso < MIN_DIAS_ATRASO_PREJUDICIAL:
            continue
        paid_at = c["paid_at"]
        if paid_at is not None and paid_at <= t_local:
            continue
        pid = c["prestamo_id"]
        counts[pid] = counts.get(pid, 0) + 1

    out: set[int] = set()
    for pid, n in counts.items():
        if PREJUDICIAL_MIN_CUOTAS_CON_ATRASO_60 <= n <= PREJUDICIAL_MAX_CUOTAS_CON_ATRASO_60:
            out.add(pid)
    return out


def _stock_1_cuota_at_midnight(
    cuotas_meta: list[dict[str, Any]], d: date, z: ZoneInfo
) -> set[int]:
    return _stock_1_cuota_at(
        cuotas_meta, datetime.combine(d, time(0, 0, 0), tzinfo=z), z
    )


def _stock_2_cuotas_at_midnight(
    cuotas_meta: list[dict[str, Any]], d: date, z: ZoneInfo
) -> set[int]:
    return _stock_2_cuotas_at(
        cuotas_meta, datetime.combine(d, time(0, 0, 0), tzinfo=z), z
    )


def _load_cuotas_meta(
    db: Session, *, fv_min: date | None, fv_max: date, z: ZoneInfo
) -> list[dict[str, Any]]:
    q = (
        select(
            Cuota.id,
            Cuota.prestamo_id,
            Cuota.fecha_vencimiento,
            Cuota.monto,
            Cuota.fecha_pago,
        )
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(Cuota.fecha_vencimiento.isnot(None))
        .where(Cuota.fecha_vencimiento <= fv_max)
        .where(_prestamo_no_excluido_notif())
        .where(sql_cliente_sin_desistimiento())
    )
    if fv_min is not None:
        q = q.where(Cuota.fecha_vencimiento >= fv_min)
    rows = db.execute(q).all()
    if not rows:
        return []

    cuota_ids = [int(r[0]) for r in rows]
    eventos_por_cuota: dict[int, list[tuple[datetime, float, bool]]] = {
        i: [] for i in cuota_ids
    }
    chunk = 2000
    for i in range(0, len(cuota_ids), chunk):
        batch = cuota_ids[i : i + chunk]
        q_pagos = select(
            CuotaPago.cuota_id,
            CuotaPago.fecha_aplicacion,
            CuotaPago.monto_aplicado,
            CuotaPago.es_pago_completo,
        ).where(CuotaPago.cuota_id.in_(batch))
        for cid, fa, mon, completo in db.execute(q_pagos).all():
            if fa is None:
                continue
            eventos_por_cuota.setdefault(int(cid), []).append(
                (_as_aware(fa, z), float(mon or 0.0), bool(completo))
            )
    for cid in eventos_por_cuota:
        eventos_por_cuota[cid].sort(key=lambda x: x[0])

    out: list[dict[str, Any]] = []
    for cid, pid, fv, monto, fp in rows:
        if not isinstance(fv, date):
            continue
        paid_at = _paid_at_caracas(
            fecha_pago=fp if isinstance(fp, date) else None,
            monto=float(monto or 0.0),
            eventos=eventos_por_cuota.get(int(cid), []),
            z=z,
        )
        out.append({"prestamo_id": int(pid), "fv": fv, "paid_at": paid_at})
    return out


def _t_fin_dia(d: date, hoy: date, now_z: datetime, z: ZoneInfo) -> datetime:
    """23:00 Caracas del dia; si es hoy y aun no son las 23:00, usa ahora (vivo)."""
    t23 = datetime.combine(d, time(23, 0, 0), tzinfo=z)
    if d == hoy and now_z < t23:
        return now_z
    return t23


def _compute_desempeno_diario(
    db: Session,
    dias: int,
    *,
    tipo_tab: str,
    stock_fn: Callable[[list[dict[str, Any]], datetime, ZoneInfo], set[int]],
    fv_min: date | None,
    fv_max: date,
    log_label: str,
) -> dict[str, Any]:
    try:
        dias_ef = min(90, max(7, int(dias)))
        z = ZoneInfo(TZ_NEGOCIO)
        hoy = hoy_negocio()
        inicio = hoy - timedelta(days=dias_ef - 1)
        now_z = datetime.now(z)

        cuotas_meta = _load_cuotas_meta(db, fv_min=fv_min, fv_max=fv_max, z=z)

        serie: list[dict[str, Any]] = []
        d = inicio
        while d <= hoy:
            t0 = datetime.combine(d, time(0, 0, 0), tzinfo=z)
            t_fin = _t_fin_dia(d, hoy, now_z, z)
            set_00 = stock_fn(cuotas_meta, t0, z) if cuotas_meta else set()
            set_fin = stock_fn(cuotas_meta, t_fin, z) if cuotas_meta else set()
            # Fin dia: del stock de las 00:00, los que siguen sin pagar a las 23:00.
            sin_pagar = set_00 & set_fin
            morosos = len(set_00)
            fin_dia = len(sin_pagar)
            serie.append(
                {
                    "fecha": d.isoformat(),
                    "dia": f"{d.day} {_NOMBRES_MES[d.month - 1]}",
                    # Campo historico del grafico «Fin dia» (ya no es SMTP).
                    "notificaciones": fin_dia,
                    "morosos": morosos,
                    "stock_00h": morosos,
                    "stock_23h": fin_dia,
                }
            )
            d += timedelta(days=1)

        return {
            "dias": dias_ef,
            "serie": serie,
            "origen": "bd",
            "tipo_tab": tipo_tab,
            "metrica_fin_dia": "stock_sin_pagar_23h",
            "serie_diaria": [
                {
                    "fecha": r["fecha"],
                    "dia": r["dia"],
                    "stock": r["stock_00h"],
                    "stock_23h": r["stock_23h"],
                }
                for r in serie
            ],
        }
    except Exception as e:
        logger.exception("Error en %s: %s", log_label, e)
        return {
            "dias": dias,
            "serie": [],
            "serie_diaria": [],
            "origen": "bd",
            "tipo_tab": tipo_tab,
            "metrica_fin_dia": "stock_sin_pagar_23h",
        }


def compute_desempeno_1_cuota_diario(db: Session, dias: int = 20) -> dict[str, Any]:
    hoy = hoy_negocio()
    inicio = hoy - timedelta(days=min(90, max(7, int(dias))) - 1)
    fv_min = (inicio - timedelta(days=1)) - timedelta(
        days=MAX_DIAS_ATRASO_PARA_LISTADO_10_DIAS
    )
    fv_max = hoy - timedelta(days=1)
    return _compute_desempeno_diario(
        db,
        dias,
        tipo_tab=TIPO_TAB_1_CUOTA,
        stock_fn=_stock_1_cuota_at,
        fv_min=fv_min,
        fv_max=fv_max,
        log_label="desempeno-1-cuota-diario",
    )


def compute_desempeno_2_cuotas_diario(db: Session, dias: int = 20) -> dict[str, Any]:
    hoy = hoy_negocio()
    fv_max = hoy - timedelta(days=MIN_DIAS_ATRASO_PREJUDICIAL)
    return _compute_desempeno_diario(
        db,
        dias,
        tipo_tab=TIPO_TAB_2_CUOTAS,
        stock_fn=_stock_2_cuotas_at,
        fv_min=None,
        fv_max=fv_max,
        log_label="desempeno-2-cuotas-diario",
    )


def compute_desempeno_1_cuota_stock(db: Session, dias: int = 20) -> dict[str, Any]:
    return compute_desempeno_1_cuota_diario(db, dias)


def compute_desempeno_2_cuotas_stock(db: Session, dias: int = 20) -> dict[str, Any]:
    return compute_desempeno_2_cuotas_diario(db, dias)
