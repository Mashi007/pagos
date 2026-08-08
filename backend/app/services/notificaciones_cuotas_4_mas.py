# -*- coding: utf-8 -*-
"""
Elegibilidad CUOTAS_4_MAS: cedulas del Excel universo con >=4 cuotas vencidas
(atraso >= 1 dia).

Modulo INDEPENDIENTE (clon de Cobranzas Excel con umbral >=4):
- no usa regla PREJUDICIAL ni solapa con COBRANZAS_EXCEL (>=2 y <4)
- plantilla, tipo_tab, config envios y endpoints propios
- nunca entra en cron ni en enviar-todas (solo manual)
- su listado/envio no se bloquea por PREJUDICIAL
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import List, Optional, Set, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.prestamo import Prestamo
from app.services.notificacion_service import (
    CUOTA_ESTADO_NO_PAGADA_PARA_NOTIF,
    SALDO_PENDIENTE_CUOTA,
    TOL_SALDO_CUOTA_NOTIFICACION,
    _item_tab,
    _prestamo_no_excluido_notif,
    enriquecer_items_notificacion_revision_manual,
    hoy_negocio,
    sum_saldo_pendiente_total_por_prestamos,
)
from app.services.notificaciones_exclusion_desistimiento import (
    sql_cliente_sin_desistimiento,
)
from app.utils.cedula_almacenamiento import texto_cedula_comparable_bd

logger = logging.getLogger(__name__)

MIN_CUOTAS_ATRASADAS_CUOTAS_4_MAS = 4


def _where_cuota_atrasada_base(fv_max_atraso: date):
    """Cuota impaga notificable con atraso >= 1 dia (fv <= hoy-1)."""
    return (
        Cuota.fecha_pago.is_(None),
        CUOTA_ESTADO_NO_PAGADA_PARA_NOTIF,
        Cuota.fecha_vencimiento.isnot(None),
        Cuota.fecha_vencimiento <= fv_max_atraso,
        SALDO_PENDIENTE_CUOTA > TOL_SALDO_CUOTA_NOTIFICACION,
        _prestamo_no_excluido_notif(),
        sql_cliente_sin_desistimiento(),
    )


def select_prestamos_cuotas_4_mas(
    db: Session, fecha_referencia: Optional[date] = None
) -> List[Tuple[int, int, int]]:
    """
    Prestamos con >=4 cuotas atrasadas (atraso >= 1 dia). Sin Excel universo.
    """
    if db is None:
        return []
    hoy = fecha_referencia or hoy_negocio()
    fv_max_atraso = hoy - timedelta(days=1)
    q = (
        select(
            Prestamo.id.label("prestamo_id"),
            Prestamo.cliente_id.label("cliente_id"),
            func.count(Cuota.id).label("total_atrasadas"),
        )
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(*_where_cuota_atrasada_base(fv_max_atraso))
        .group_by(Prestamo.id, Prestamo.cliente_id)
        .having(func.count(Cuota.id) >= MIN_CUOTAS_ATRASADAS_CUOTAS_4_MAS)
    )
    rows = db.execute(q).all()
    out: List[Tuple[int, int, int]] = []
    for pid, cid, total in rows:
        if pid is None or cid is None:
            continue
        out.append((int(pid), int(cid), int(total or 0)))
    return out


def clientes_en_regla_cuotas_4_mas(
    db: Session, fecha_referencia: Optional[date] = None
) -> Tuple[Set[int], Set[str]]:
    """
    (cliente_ids, cedulas_comparables) de titulares en CUOTAS_4_MAS.
    Las cedulas se guardan crudas y normalizadas para matching.
    """
    cliente_ids: Set[int] = set()
    cedulas: Set[str] = set()
    if db is None:
        return cliente_ids, cedulas
    rows = select_prestamos_cuotas_4_mas(db, fecha_referencia)
    if not rows:
        return cliente_ids, cedulas
    cids = sorted({cid for _, cid, _ in rows})
    ced_map = {
        int(r[0]): str(r[1] or "").strip()
        for r in db.execute(
            select(Cliente.id, Cliente.cedula).where(Cliente.id.in_(cids))
        ).all()
        if r[0] is not None
    }
    for _, cid, _ in rows:
        cliente_ids.add(int(cid))
        ced = ced_map.get(int(cid), "")
        if ced:
            cedulas.add(ced)
            key = texto_cedula_comparable_bd(ced)
            if key:
                cedulas.add(key)
    return cliente_ids, cedulas


def _as_date(val) -> Optional[date]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str) and val.strip():
        try:
            return date.fromisoformat(val.strip()[:10])
        except ValueError:
            return None
    return None


def item_cumple_regla_cuotas_4_mas(
    item: dict,
    fecha_referencia: Optional[date] = None,
    *,
    claves_universo_set: Optional[Set[str]] = None,
) -> bool:
    """
    Cinturon: n>=4 overdue, cedula en universo, dias_atraso>=1 (o fv implica >=1).
    No aplica reglas PREJUDICIAL (>=2 atrasadas, atraso >=1; modulo activo).
    """
    if not isinstance(item, dict):
        return False
    try:
        total = int(
            item.get("total_cuotas_atrasadas") or item.get("cuotas_atrasadas") or 0
        )
    except (TypeError, ValueError):
        total = 0
    if total < MIN_CUOTAS_ATRASADAS_CUOTAS_4_MAS:
        return False

    ced = str(item.get("cedula") or "").strip()
    key = texto_cedula_comparable_bd(ced) if ced else ""
    if not key:
        return False
    # claves_universo_set ignorado (sin filtro Excel).
    del claves_universo_set

    hoy = fecha_referencia or hoy_negocio()
    dias = item.get("dias_atraso")
    try:
        if dias is not None and int(dias) >= 1:
            return True
    except (TypeError, ValueError):
        pass
    fv = _as_date(item.get("fecha_vencimiento"))
    if fv is None:
        return False
    return (hoy - fv).days >= 1


def build_cuotas_4_mas_items(
    db: Session, fecha_referencia: Optional[date] = None
) -> List[dict]:
    """
    Lista CUOTAS_4_MAS: misma forma de item que cobranzas/prejudicial
    (un item por prestamo; cuota de referencia = mas antigua atrasada).
    """
    hoy = fecha_referencia or hoy_negocio()
    fv_max = hoy - timedelta(days=1)
    rows = select_prestamos_cuotas_4_mas(db, fecha_referencia=hoy)
    if not rows:
        return []

    prestamo_ids = [pid for pid, _cid, _tot in rows]
    totals_by_prestamo = {pid: tot for pid, _cid, tot in rows}
    cliente_ids = sorted({cid for _pid, cid, _tot in rows})

    clientes_map = {
        c.id: c
        for c in db.scalars(select(Cliente).where(Cliente.id.in_(cliente_ids))).all()
    }

    cuotas_rows = db.execute(
        select(Cuota, Prestamo.cliente_id)
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .where(
            Prestamo.id.in_(prestamo_ids),
            *_where_cuota_atrasada_base(fv_max),
        )
        .order_by(Cuota.fecha_vencimiento.asc(), Cuota.id.asc())
    ).all()

    primera_por_prestamo: dict = {}
    cliente_por_prestamo: dict = {}
    for c, titular_id in cuotas_rows:
        pid = int(c.prestamo_id) if c.prestamo_id is not None else None
        if pid is None:
            continue
        if pid not in primera_por_prestamo:
            primera_por_prestamo[pid] = c
            if titular_id is not None:
                cliente_por_prestamo[pid] = int(titular_id)

    totales = sum_saldo_pendiente_total_por_prestamos(db, prestamo_ids)
    items: List[dict] = []
    omitidos = 0
    for pid in prestamo_ids:
        total_cuotas = totals_by_prestamo.get(pid, 0)
        cuota_ref = primera_por_prestamo.get(pid)
        cid = cliente_por_prestamo.get(pid)
        cliente = clientes_map.get(cid) if cid is not None else None
        if not cliente or not cuota_ref:
            omitidos += 1
            continue
        if total_cuotas < MIN_CUOTAS_ATRASADAS_CUOTAS_4_MAS:
            omitidos += 1
            continue
        fv = getattr(cuota_ref, "fecha_vencimiento", None)
        if fv is None:
            omitidos += 1
            continue
        dias = (hoy - fv).days if hasattr(fv, "year") else -1
        if dias < 1:
            omitidos += 1
            continue
        tp = totales.get(int(pid))
        item = _item_tab(cliente, cuota_ref, total_pendiente_pagar=tp)
        item["total_cuotas_atrasadas"] = total_cuotas
        item["cuotas_atrasadas"] = total_cuotas
        item["dias_atraso"] = dias
        item["prestamo_id"] = int(pid)
        if not item_cumple_regla_cuotas_4_mas(item, hoy):
            omitidos += 1
            continue
        items.append(item)
    if omitidos:
        logger.info(
            "[cuotas_4_mas] omitidos_fuera_de_regla=%s incluidos=%s",
            omitidos,
            len(items),
        )
    enriquecer_items_notificacion_revision_manual(db, items)
    return items
