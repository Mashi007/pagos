"""
Exclusion mutua entre segmentos de mora y elegibilidad «2 Cuotas» (PREJUDICIAL).

Regla «2 Cuotas» (innegociable):
- exactamente 2 cuotas atrasadas TOTALES en el mismo prestamo (atraso >= 1 dia),
- y ambas con atraso >= 60 dias.

Prioridad: si el titular esta en «2 Cuotas», no recibe «1 Cuota» ni «dia siguiente».
«3 dias antes» no se recorta por esta exclusion (recordatorio preventivo distinto).
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import List, Optional, Set, Tuple

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.prestamo import Prestamo
from app.services.notificacion_service import (
    CUOTA_ESTADO_NO_PAGADA_PARA_NOTIF,
    MIN_DIAS_ATRASO_PREJUDICIAL,
    PREJUDICIAL_MAX_CUOTAS_CON_ATRASO_60,
    PREJUDICIAL_MIN_CUOTAS_CON_ATRASO_60,
    SALDO_PENDIENTE_CUOTA,
    TOL_SALDO_CUOTA_NOTIFICACION,
    _prestamo_no_excluido_notif,
    hoy_negocio,
)
from app.services.notificaciones_exclusion_desistimiento import (
    sql_cliente_sin_desistimiento,
)

logger = logging.getLogger(__name__)

TIPOS_EXCLUIDOS_SI_PREJUDICIAL = frozenset(
    {
        "PAGO_1_DIA_ATRASADO",
        "PAGO_10_DIAS_ATRASADO",
    }
)


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


def select_prestamos_prejudicial(
    db: Session, fecha_referencia: Optional[date] = None
) -> List[Tuple[int, int, int]]:
    """
    Prestamos que cumplen «2 Cuotas».

    Returns list of (prestamo_id, cliente_id, total_cuotas_atrasadas=2).
    Fail-closed: propaga errores de BD.
    """
    if db is None:
        return []
    hoy = fecha_referencia or hoy_negocio()
    fv_max_atraso = hoy - timedelta(days=1)
    fv_max_60 = hoy - timedelta(days=MIN_DIAS_ATRASO_PREJUDICIAL)
    n_ge_60 = func.coalesce(
        func.sum(case((Cuota.fecha_vencimiento <= fv_max_60, 1), else_=0)),
        0,
    )
    q = (
        select(
            Prestamo.id.label("prestamo_id"),
            Prestamo.cliente_id.label("cliente_id"),
            func.count(Cuota.id).label("total_atrasadas"),
        )
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .where(*_where_cuota_atrasada_base(fv_max_atraso))
        .group_by(Prestamo.id, Prestamo.cliente_id)
        .having(
            func.count(Cuota.id) >= PREJUDICIAL_MIN_CUOTAS_CON_ATRASO_60,
            func.count(Cuota.id) <= PREJUDICIAL_MAX_CUOTAS_CON_ATRASO_60,
            n_ge_60 >= PREJUDICIAL_MIN_CUOTAS_CON_ATRASO_60,
            n_ge_60 <= PREJUDICIAL_MAX_CUOTAS_CON_ATRASO_60,
        )
    )
    rows = db.execute(q).all()
    out: List[Tuple[int, int, int]] = []
    for pid, cid, total in rows:
        if pid is None or cid is None:
            continue
        out.append((int(pid), int(cid), int(total or 0)))
    return out


def clientes_en_regla_prejudicial(
    db: Session, fecha_referencia: Optional[date] = None
) -> Tuple[Set[int], Set[str]]:
    """
    (cliente_ids, cedulas) de titulares en «2 Cuotas».
    Fail-closed: si la consulta falla, relanza la excepcion.
    """
    cliente_ids: Set[int] = set()
    cedulas: Set[str] = set()
    if db is None:
        return cliente_ids, cedulas
    rows = select_prestamos_prejudicial(db, fecha_referencia)
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
    return cliente_ids, cedulas


def _item_es_de_cliente(item: dict, cliente_ids: Set[int], cedulas: Set[str]) -> bool:
    if not isinstance(item, dict):
        return False
    cliente_id = item.get("cliente_id")
    try:
        cid = int(cliente_id) if cliente_id is not None else None
    except (TypeError, ValueError):
        cid = None
    if cid is not None and cid in cliente_ids:
        return True
    ced = str(item.get("cedula") or "").strip()
    return bool(ced) and ced in cedulas


def filtrar_items_sin_prejudicial(
    db: Session,
    items: List[dict],
    fecha_referencia: Optional[date] = None,
    *,
    claves: Optional[Tuple[Set[int], Set[str]]] = None,
    etiqueta: str = "listado",
) -> List[dict]:
    """Quita de ``items`` los titulares que ya estan en «2 Cuotas»."""
    if not items or db is None:
        return items
    if claves is None:
        claves = clientes_en_regla_prejudicial(db, fecha_referencia)
    cliente_ids, cedulas = claves
    if not cliente_ids and not cedulas:
        return items
    filtrados = [it for it in items if not _item_es_de_cliente(it, cliente_ids, cedulas)]
    omitidos = len(items) - len(filtrados)
    if omitidos:
        logger.info(
            "[notif_dedup] %s: %s item(s) omitidos por titular ya en 2 Cuotas",
            etiqueta,
            omitidos,
        )
    return filtrados


def filtrar_items_menor_60_sin_prejudicial(
    db: Session,
    items: List[dict],
    fecha_referencia: Optional[date] = None,
) -> List[dict]:
    """Quita del listado «1 Cuota» los titulares que ya estan en «2 Cuotas»."""
    return filtrar_items_sin_prejudicial(
        db, items, fecha_referencia, etiqueta="menor-60"
    )


def item_excluido_por_prejudicial_en_envio(
    tipo: str,
    item: dict,
    cliente_ids: Set[int],
    cedulas: Set[str],
) -> bool:
    """True si este tipo+item no debe enviarse por exclusion mutua con 2 Cuotas."""
    if (tipo or "").strip() not in TIPOS_EXCLUIDOS_SI_PREJUDICIAL:
        return False
    return _item_es_de_cliente(item, cliente_ids, cedulas)


# --- COBRANZAS_EXCEL (Excel universo + >=2 atrasadas): prioridad sobre 1/2 Cuotas y dia siguiente ---

TIPOS_EXCLUIDOS_SI_COBRANZAS_EXCEL = frozenset(
    {
        "PAGO_1_DIA_ATRASADO",
        "PAGO_10_DIAS_ATRASADO",
        "PREJUDICIAL",
    }
)


def _item_es_de_cliente_cobranzas(
    item: dict, cliente_ids: Set[int], cedulas: Set[str]
) -> bool:
    """Como _item_es_de_cliente, mas match por cedula comparable (universo Excel)."""
    if _item_es_de_cliente(item, cliente_ids, cedulas):
        return True
    if not isinstance(item, dict) or not cedulas:
        return False
    from app.utils.cedula_almacenamiento import texto_cedula_comparable_bd

    ced = str(item.get("cedula") or "").strip()
    if not ced:
        return False
    key = texto_cedula_comparable_bd(ced)
    return bool(key) and key in cedulas


def filtrar_items_sin_cobranzas_excel(
    db: Session,
    items: List[dict],
    fecha_referencia: Optional[date] = None,
    *,
    claves: Optional[Tuple[Set[int], Set[str]]] = None,
    etiqueta: str = "listado",
) -> List[dict]:
    """Quita de ``items`` los titulares que ya estan en COBRANZAS_EXCEL."""
    if not items or db is None:
        return items
    if claves is None:
        from app.services.notificaciones_cobranzas_excel import (
            clientes_en_regla_cobranzas_excel,
        )

        claves = clientes_en_regla_cobranzas_excel(db, fecha_referencia)
    cliente_ids, cedulas = claves
    if not cliente_ids and not cedulas:
        return items
    filtrados = [
        it for it in items if not _item_es_de_cliente_cobranzas(it, cliente_ids, cedulas)
    ]
    omitidos = len(items) - len(filtrados)
    if omitidos:
        logger.info(
            "[notif_dedup] %s: %s item(s) omitidos por titular ya en Cobranzas Excel",
            etiqueta,
            omitidos,
        )
    return filtrados


def item_excluido_por_cobranzas_excel_en_envio(
    tipo: str,
    item: dict,
    cliente_ids: Set[int],
    cedulas: Set[str],
) -> bool:
    """True si este tipo+item no debe enviarse por exclusion mutua con Cobranzas Excel."""
    if (tipo or "").strip() not in TIPOS_EXCLUIDOS_SI_COBRANZAS_EXCEL:
        return False
    return _item_es_de_cliente_cobranzas(item, cliente_ids, cedulas)
