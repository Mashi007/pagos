"""
Desempeño diario de cartera (independiente de envíos SMTP):

Segmentos excluyentes:
- 1 cuota: exactamente 1, atraso 1–30 (desde el día siguiente al vencimiento).
- 2 cuotas: exactamente 2, atraso max 6–60.
- 3 cuotas: exactamente 3, atraso max 6–90.
- 4 cuotas: exactamente 4, atraso max 6–120.
- 5 cuotas: exactamente 5, atraso max 6–150.
- 6+: 6 o mas, atraso min 6 (sin techo).
1 cuota excluye titulares que el mismo dia tienen >=2 cuotas atrasadas (desde dia 1).

Por día (últimos N, Caracas):
1) Inicio día (morosos / stock_00h) — nivel a las 00:00.
2) Fin dia — del stock 00:00, cuántos siguen a las 23:00 (o ahora si es hoy).
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
    PREJUDICIAL_MIN_CUOTAS_CON_ATRASO_60,
    TOL_SALDO_CUOTA_NOTIFICACION,
    _prestamo_no_excluido_notif,
)

# Segmentos por cantidad de cuotas atrasadas (día 1+). Sin tope de días.
# Exacto 1..15; gráficos «6+» = >=6; tabla resto6plus = >=16.
SEG_MIN_DIAS_ATRASO = 1
SEG_MIN_DIAS_CUOTA_1 = 1
# Cobranzas / 1 cuota: retira atraso 1–5 días; el resto (6+) sigue en 1 cuota.
SEG_MIN_DIAS_COBRANZAS_1_CUOTA = 6
SEG_MAX_N_EXACTO = 15
from app.services.notificaciones_exclusion_desistimiento import sql_cliente_sin_desistimiento

logger = logging.getLogger(__name__)

_NOMBRES_MES = (
    "Ene", "Feb", "Mar", "Abr", "May", "Jun",
    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
)
TIPO_TAB_1_CUOTA = "dias_10_retraso"
TIPO_TAB_2_CUOTAS = "prejudicial"
TIPO_TAB_3_CUOTAS = "3_cuotas"
TIPO_TAB_4_CUOTAS = "4_cuotas"
TIPO_TAB_5_CUOTAS = "5_cuotas"
TIPO_TAB_6PLUS_CUOTAS = "6plus_cuotas"
# Compat: nombre histórico del tab 4+ (ahora es exactamente 4).
TIPO_TAB_4PLUS_CUOTAS = TIPO_TAB_4_CUOTAS

CasoDesempeno = Literal[
    "1_cuota", "2_cuotas", "3_cuotas", "4_cuotas", "5_cuotas", "6plus_cuotas"
]


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
        # Solo fecha (sin cuota_pago): asumir pago en el dia, ANTES del corte Fin dia
        # (23:00). Si se usara 23:59:59, Fin dia del mismo dia nunca bajaria.
        return datetime.combine(fecha_pago, time(12, 0, 0), tzinfo=z)
    return None


def _cuotas_atrasadas_para_segmento(
    cuotas_meta: list[dict[str, Any]],
    t_ref: datetime,
    z: ZoneInfo,
    *,
    min_dias: int | None = None,
) -> dict[int, list[int]]:
    """Cuotas vencidas sin pago hasta t_ref (atraso >= min_dias, default día 1)."""
    floor = SEG_MIN_DIAS_ATRASO if min_dias is None else int(min_dias)
    t_local = _as_aware(t_ref, z)
    d = t_local.date()
    overdue: dict[int, list[int]] = {}
    for c in cuotas_meta:
        fv = c["fv"]
        if fv >= d:
            continue
        dias_atraso = (d - fv).days
        if dias_atraso < floor:
            continue
        paid_at = c["paid_at"]
        if paid_at is not None and paid_at <= t_local:
            continue
        overdue.setdefault(c["prestamo_id"], []).append(dias_atraso)
    return overdue


def _cumple_ventana_segmento(dias_list: list[int], n: int) -> bool:
    """Exactamente n cuotas atrasadas (1..15). Ignora días de atraso."""
    if not dias_list or n < 1 or n > SEG_MAX_N_EXACTO:
        return False
    return len(dias_list) == n


def _cumple_ventana_6plus(dias_list: list[int]) -> bool:
    """6 o más cuotas atrasadas (cualquier antigüedad). Gráficos/serie."""
    return bool(dias_list) and len(dias_list) >= 6


def _stock_1_cuota_at(
    cuotas_meta: list[dict[str, Any]], t_ref: datetime, z: ZoneInfo
) -> set[int]:
    """Segmento 1: exactamente 1 cuota atrasada."""
    overdue = _cuotas_atrasadas_para_segmento(
        cuotas_meta, t_ref, z, min_dias=SEG_MIN_DIAS_CUOTA_1
    )
    return {
        pid
        for pid, dias_list in overdue.items()
        if len(dias_list) == 1 and _cumple_ventana_segmento(dias_list, 1)
    }


def _overdue_by_prestamo(
    cuotas_meta: list[dict[str, Any]], t_ref: datetime, z: ZoneInfo
) -> dict[int, list[int]]:
    """Alias: cuotas atrasadas para segmentación (día 1+)."""
    return _cuotas_atrasadas_para_segmento(
        cuotas_meta, t_ref, z, min_dias=SEG_MIN_DIAS_CUOTA_1
    )


def _stock_exact_n_cuotas_at(
    cuotas_meta: list[dict[str, Any]], t_ref: datetime, z: ZoneInfo, n: int
) -> set[int]:
    """Exactamente n cuotas atrasadas (sin tope de días)."""
    overdue = _cuotas_atrasadas_para_segmento(
        cuotas_meta, t_ref, z, min_dias=SEG_MIN_DIAS_CUOTA_1
    )
    return {
        pid
        for pid, dias_list in overdue.items()
        if len(dias_list) == n and _cumple_ventana_segmento(dias_list, n)
    }


def _stock_2_cuotas_at(
    cuotas_meta: list[dict[str, Any]], t_ref: datetime, z: ZoneInfo
) -> set[int]:
    """Exactamente 2 cuotas atrasadas. Excluyente."""
    return _stock_exact_n_cuotas_at(cuotas_meta, t_ref, z, 2)


def _stock_3_cuotas_at(
    cuotas_meta: list[dict[str, Any]], t_ref: datetime, z: ZoneInfo
) -> set[int]:
    """Exactamente 3 cuotas atrasadas. Excluyente."""
    return _stock_exact_n_cuotas_at(cuotas_meta, t_ref, z, 3)


def _stock_4_cuotas_at(
    cuotas_meta: list[dict[str, Any]], t_ref: datetime, z: ZoneInfo
) -> set[int]:
    """Exactamente 4 cuotas atrasadas. Excluyente."""
    return _stock_exact_n_cuotas_at(cuotas_meta, t_ref, z, 4)


def _stock_5_cuotas_at(
    cuotas_meta: list[dict[str, Any]], t_ref: datetime, z: ZoneInfo
) -> set[int]:
    """Exactamente 5 cuotas atrasadas. Excluyente."""
    return _stock_exact_n_cuotas_at(cuotas_meta, t_ref, z, 5)


def _stock_6plus_cuotas_at(
    cuotas_meta: list[dict[str, Any]], t_ref: datetime, z: ZoneInfo
) -> set[int]:
    """6 o más cuotas atrasadas. Excluyente (gráficos)."""
    overdue = _cuotas_atrasadas_para_segmento(
        cuotas_meta, t_ref, z, min_dias=SEG_MIN_DIAS_CUOTA_1
    )
    return {
        pid
        for pid, dias_list in overdue.items()
        if _cumple_ventana_6plus(dias_list)
    }


def _stock_4plus_cuotas_at(
    cuotas_meta: list[dict[str, Any]], t_ref: datetime, z: ZoneInfo
) -> set[int]:
    """Compat: antes era 4+; ahora es exactamente 4 (misma regla que 2/3)."""
    return _stock_4_cuotas_at(cuotas_meta, t_ref, z)


def _stock_ge2_cuotas_at(
    cuotas_meta: list[dict[str, Any]], t_ref: datetime, z: ZoneInfo
) -> set[int]:
    """Prestamos con >=2 cuotas atrasadas desde dia 1 (exclusion mutua vs 1 cuota)."""
    overdue = _cuotas_atrasadas_para_segmento(
        cuotas_meta, t_ref, z, min_dias=SEG_MIN_DIAS_CUOTA_1
    )
    return {
        pid
        for pid, dias_list in overdue.items()
        if len(dias_list) >= PREJUDICIAL_MIN_CUOTAS_CON_ATRASO_60
    }


def _cliente_ids_de_prestamos(
    cuotas_meta: list[dict[str, Any]], prestamo_ids: set[int]
) -> set[int]:
    out: set[int] = set()
    for c in cuotas_meta:
        if c["prestamo_id"] not in prestamo_ids:
            continue
        cid = c.get("cliente_id")
        if cid is not None:
            out.add(int(cid))
    return out


def _stock_1_cuota_excluyendo_prejudicial_at(
    cuotas_meta: list[dict[str, Any]], t_ref: datetime, z: ZoneInfo
) -> set[int]:
    """1 cuota sin titulares que el mismo instante tienen >=2 cuotas atrasadas."""
    set_1 = _stock_1_cuota_at(cuotas_meta, t_ref, z)
    if not set_1:
        return set_1
    set_ge2 = _stock_ge2_cuotas_at(cuotas_meta, t_ref, z)
    if not set_ge2:
        return set_1
    clientes_ge2 = _cliente_ids_de_prestamos(cuotas_meta, set_ge2)
    if not clientes_ge2:
        return set_1
    pid_a_cliente: dict[int, int | None] = {}
    for c in cuotas_meta:
        pid = c["prestamo_id"]
        if pid not in pid_a_cliente:
            pid_a_cliente[pid] = c.get("cliente_id")
    return {
        pid
        for pid in set_1
        if pid_a_cliente.get(pid) not in clientes_ge2
    }


def _stock_1_cuota_cobranzas_at(
    cuotas_meta: list[dict[str, Any]], t_ref: datetime, z: ZoneInfo
) -> set[int]:
    """1 cuota en Cobranzas: exactamente 1 atrasada y atraso >= 6 días."""
    set_1 = _stock_1_cuota_excluyendo_prejudicial_at(cuotas_meta, t_ref, z)
    if not set_1:
        return set_1
    overdue = _cuotas_atrasadas_para_segmento(
        cuotas_meta, t_ref, z, min_dias=SEG_MIN_DIAS_CUOTA_1
    )
    return {
        pid
        for pid in set_1
        if max(overdue.get(pid) or [0]) >= SEG_MIN_DIAS_COBRANZAS_1_CUOTA
    }


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
            Prestamo.cliente_id,
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
    for cid, pid, cliente_id, fv, monto, fp in rows:
        if not isinstance(fv, date):
            continue
        paid_at = _paid_at_caracas(
            fecha_pago=fp if isinstance(fp, date) else None,
            monto=float(monto or 0.0),
            eventos=eventos_por_cuota.get(int(cid), []),
            z=z,
        )
        try:
            cid_int = int(cliente_id) if cliente_id is not None else None
        except (TypeError, ValueError):
            cid_int = None
        out.append(
            {
                "prestamo_id": int(pid),
                "cliente_id": cid_int,
                "fv": fv,
                "paid_at": paid_at,
            }
        )
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
            # Misma foto que Cobranzas: N atrasadas as-of (00:00 / 23:00 o ahora).
            morosos = len(set_00)
            fin_dia = len(set_fin)
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
            "metrica_fin_dia": "stock_asof_fin_dia",
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
            "metrica_fin_dia": "stock_asof_fin_dia",
        }


def compute_desempeno_1_cuota_diario(db: Session, dias: int = 20) -> dict[str, Any]:
    hoy = hoy_negocio()
    # fv_min=None: hace falta cargar cuotas >=60d para saber que titulares
    # estan en 2 cuotas y excluirlos del grafico 1 cuota (exclusion mutua).
    fv_max = hoy - timedelta(days=1)
    return _compute_desempeno_diario(
        db,
        dias,
        tipo_tab=TIPO_TAB_1_CUOTA,
        stock_fn=_stock_1_cuota_cobranzas_at,
        fv_min=None,
        fv_max=fv_max,
        log_label="desempeno-1-cuota-diario",
    )


def compute_desempeno_2_cuotas_diario(db: Session, dias: int = 20) -> dict[str, Any]:
    hoy = hoy_negocio()
    fv_max = hoy - timedelta(days=1)
    return _compute_desempeno_diario(
        db,
        dias,
        tipo_tab=TIPO_TAB_2_CUOTAS,
        stock_fn=_stock_2_cuotas_at,
        fv_min=None,
        fv_max=fv_max,
        log_label="desempeno-2-cuotas-diario",
    )


def compute_desempeno_3_cuotas_diario(db: Session, dias: int = 20) -> dict[str, Any]:
    hoy = hoy_negocio()
    fv_max = hoy - timedelta(days=1)
    return _compute_desempeno_diario(
        db,
        dias,
        tipo_tab=TIPO_TAB_3_CUOTAS,
        stock_fn=_stock_3_cuotas_at,
        fv_min=None,
        fv_max=fv_max,
        log_label="desempeno-3-cuotas-diario",
    )


def compute_desempeno_4plus_cuotas_diario(db: Session, dias: int = 20) -> dict[str, Any]:
    """Compat: endpoint histórico 4+ ahora = exactamente 4 cuotas (6–120)."""
    return compute_desempeno_4_cuotas_diario(db, dias)


def compute_desempeno_4_cuotas_diario(db: Session, dias: int = 20) -> dict[str, Any]:
    hoy = hoy_negocio()
    fv_max = hoy - timedelta(days=1)
    return _compute_desempeno_diario(
        db,
        dias,
        tipo_tab=TIPO_TAB_4_CUOTAS,
        stock_fn=_stock_4_cuotas_at,
        fv_min=None,
        fv_max=fv_max,
        log_label="desempeno-4-cuotas-diario",
    )


def compute_desempeno_5_cuotas_diario(db: Session, dias: int = 20) -> dict[str, Any]:
    hoy = hoy_negocio()
    fv_max = hoy - timedelta(days=1)
    return _compute_desempeno_diario(
        db,
        dias,
        tipo_tab=TIPO_TAB_5_CUOTAS,
        stock_fn=_stock_5_cuotas_at,
        fv_min=None,
        fv_max=fv_max,
        log_label="desempeno-5-cuotas-diario",
    )


def compute_desempeno_6plus_cuotas_diario(db: Session, dias: int = 20) -> dict[str, Any]:
    hoy = hoy_negocio()
    fv_max = hoy - timedelta(days=1)
    return _compute_desempeno_diario(
        db,
        dias,
        tipo_tab=TIPO_TAB_6PLUS_CUOTAS,
        stock_fn=_stock_6plus_cuotas_at,
        fv_min=None,
        fv_max=fv_max,
        log_label="desempeno-6plus-cuotas-diario",
    )


def compute_desempeno_1_cuota_stock(db: Session, dias: int = 20) -> dict[str, Any]:
    return compute_desempeno_1_cuota_diario(db, dias)


def compute_desempeno_2_cuotas_stock(db: Session, dias: int = 20) -> dict[str, Any]:
    return compute_desempeno_2_cuotas_diario(db, dias)


def compute_desempeno_3_cuotas_stock(db: Session, dias: int = 20) -> dict[str, Any]:
    return compute_desempeno_3_cuotas_diario(db, dias)


def compute_desempeno_4plus_cuotas_stock(db: Session, dias: int = 20) -> dict[str, Any]:
    return compute_desempeno_4_cuotas_diario(db, dias)


def compute_desempeno_4_cuotas_stock(db: Session, dias: int = 20) -> dict[str, Any]:
    return compute_desempeno_4_cuotas_diario(db, dias)


def compute_desempeno_5_cuotas_stock(db: Session, dias: int = 20) -> dict[str, Any]:
    return compute_desempeno_5_cuotas_diario(db, dias)


def compute_desempeno_6plus_cuotas_stock(db: Session, dias: int = 20) -> dict[str, Any]:
    return compute_desempeno_6plus_cuotas_diario(db, dias)
