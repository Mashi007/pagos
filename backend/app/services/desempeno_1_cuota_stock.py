"""
Desempeño diario «1 cuota» (dias_10_retraso):

1) notificaciones — envíos SMTP exitosos ese día (envios_notificacion).
2) morosos — nivel (stock) de préstamos en listado 1 cuota a las 00:00 de ese día
   (ej. día 21 = 991, día 22 = 890). No es el flujo de «nuevos» del día.

Dos cantidades por día, misma escala aproximada para comparar desempeño.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import Date, case, cast, func, select
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.cuota_pago import CuotaPago
from app.models.envio_notificacion import EnvioNotificacion
from app.models.prestamo import Prestamo
from app.services.cuota_estado import TZ_NEGOCIO, hoy_negocio
from app.services.notificacion_service import (
    MAX_DIAS_ATRASO_PARA_LISTADO_10_DIAS,
    MIN_DIAS_ATRASO_PARA_LISTADO_10_DIAS,
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


def _stock_prestamo_ids_at_midnight(
    cuotas_meta: list[dict[str, Any]],
    d: date,
    z: ZoneInfo,
) -> set[int]:
    """Préstamos en 1 cuota (atraso 6–59, exactamente 1) a las 00:00 de `d` (Caracas)."""
    t_ref = datetime.combine(d, time(0, 0, 0), tzinfo=z)
    overdue: dict[int, list[int]] = {}
    for c in cuotas_meta:
        fv = c["fv"]
        if fv >= d:
            continue
        dias_atraso = (d - fv).days
        if dias_atraso < 1:
            continue
        paid_at = c["paid_at"]
        if paid_at is not None and paid_at <= t_ref:
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


def _notificaciones_por_dia(db: Session, inicio: date, hoy: date, z: ZoneInfo) -> dict[date, int]:
    start_local = datetime.combine(inicio, time.min, tzinfo=z)
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
    stmt = (
        select(dia_expr.label("dia"), enviados_sum.label("enviados"))
        .where(
            EnvioNotificacion.tipo_tab == TIPO_TAB_1_CUOTA,
            EnvioNotificacion.fecha_envio >= start_utc_naive,
        )
        .group_by(dia_expr)
    )
    counts: dict[date, int] = {}
    for row in db.execute(stmt).all():
        d = row.dia
        if isinstance(d, datetime):
            d = d.date()
        if not isinstance(d, date):
            continue
        if d < inicio or d > hoy:
            continue
        counts[d] = int(row.enviados or 0)
    return counts


def compute_desempeno_1_cuota_stock(db: Session, dias: int = 20) -> dict[str, Any]:
    """
    Compat: mismo nombre de función usado por el endpoint.
    Devuelve serie diaria con notificaciones + morosos/stock 00:00 (últimos `dias`).
    """
    return compute_desempeno_1_cuota_diario(db, dias)


def compute_desempeno_1_cuota_diario(db: Session, dias: int = 20) -> dict[str, Any]:
    try:
        dias_ef = min(90, max(7, int(dias)))
        z = ZoneInfo(TZ_NEGOCIO)
        hoy = hoy_negocio()
        inicio = hoy - timedelta(days=dias_ef - 1)

        # --- notificaciones por día ---
        notif_by_day = _notificaciones_por_dia(db, inicio, hoy, z)

        # --- sets de stock a cada medianoche (inicio-1 .. hoy) para medir entradas ---
        fv_min = (inicio - timedelta(days=1)) - timedelta(days=MAX_DIAS_ATRASO_PARA_LISTADO_10_DIAS)
        fv_max = hoy - timedelta(days=1)
        q_cuotas = (
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
            .where(Cuota.fecha_vencimiento >= fv_min)
            .where(Cuota.fecha_vencimiento <= fv_max)
            .where(_prestamo_no_excluido_notif())
            .where(sql_cliente_sin_desistimiento())
        )
        rows = db.execute(q_cuotas).all()
        cuota_ids = [int(r[0]) for r in rows]
        eventos_por_cuota: dict[int, list[tuple[datetime, float, bool]]] = {i: [] for i in cuota_ids}
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

        cuotas_meta: list[dict[str, Any]] = []
        for cid, pid, fv, monto, fp in rows:
            if not isinstance(fv, date):
                continue
            paid_at = _paid_at_caracas(
                fecha_pago=fp if isinstance(fp, date) else None,
                monto=float(monto or 0.0),
                eventos=eventos_por_cuota.get(int(cid), []),
                z=z,
            )
            cuotas_meta.append({"prestamo_id": int(pid), "fv": fv, "paid_at": paid_at})

        prev_set = _stock_prestamo_ids_at_midnight(cuotas_meta, inicio - timedelta(days=1), z)
        serie: list[dict[str, Any]] = []
        d = inicio
        while d <= hoy:
            cur_set = _stock_prestamo_ids_at_midnight(cuotas_meta, d, z)
            notif = int(notif_by_day.get(d, 0))
            morosos = len(cur_set)  # nivel a las 00:00 (desempeño / cartera 1 cuota)
            serie.append(
                {
                    "fecha": d.isoformat(),
                    "dia": f"{d.day} {_NOMBRES_MES[d.month - 1]}",
                    "notificaciones": notif,
                    "morosos": morosos,
                    "stock_00h": morosos,
                }
            )
            prev_set = cur_set
            d += timedelta(days=1)

        return {
            "dias": dias_ef,
            "serie": serie,
            "origen": "bd",
            # compat campos previos (vacíos) por si algo aún los lee
            "serie_diaria": [
                {"fecha": r["fecha"], "dia": r["dia"], "stock": r["stock_00h"]} for r in serie
            ],
        }
    except Exception as e:
        logger.exception("Error en desempeno-1-cuota-diario: %s", e)
        return {"dias": dias, "serie": [], "serie_diaria": [], "origen": "bd"}
