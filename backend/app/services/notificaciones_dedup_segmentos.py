"""
Segmentos de mora: pueden solaparse con «dia siguiente».

Dia siguiente (PAGO_1_DIA_ATRASADO):
  Cualquier cuota impaga con fecha_vencimiento = ayer (atraso calendario = 1).
  No recorta «2 Cuotas», «1 Cuota» ni «3 dias antes». Si el titular tambien
  califica en esas reglas, se envian ademas de este correo.

«2 Cuotas y mas» (PREJUDICIAL):
  Prestamo con >=2 cuotas impagas atrasadas (atraso >=1 dia), sin tope superior.
  Prioriza sobre «1 Cuota» (un titular en 2+ no recibe la plantilla de 1 cuota).

«1 Cuota» (PAGO_10_DIAS_ATRASADO):
  Exactamente 1 cuota atrasada con atraso 6-59 dias, y el titular NO esta en
  «2 Cuotas y mas».

Ademas: si un tipo_tab ya tuvo envio exitoso en envios_notificacion, el pipeline
puede omitir reenvio (salvo pestanas que permiten reenvio; ver pipeline).

COBRANZAS_EXCEL / CUOTAS_4_MAS: modulos retirados; exclusiones legacy pueden
seguir en codigo para compat. Sus exitos historicos cuentan como PREJUDICIAL.

«3 dias antes» no se recorta por dia siguiente.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import List, Optional, Set, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.prestamo import Prestamo
from app.services.notificacion_service import (
    CUOTA_ESTADO_NO_PAGADA_PARA_NOTIF,
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

# Dia siguiente ya no recorta otros casos: el titular puede recibir 2 Cuotas / 1 Cuota / 3d.
TIPOS_EXCLUIDOS_SI_DIA_SIGUIENTE = frozenset()

# Si el titular esta en «2 Cuotas», no se envia «1 Cuota».
TIPOS_EXCLUIDOS_SI_PREJUDICIAL = frozenset(
    {
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


def clientes_en_regla_dia_siguiente(
    db: Session, fecha_referencia: Optional[date] = None
) -> Tuple[Set[int], Set[str]]:
    """
    (cliente_ids, cedulas) de titulares con al menos una cuota impaga
    con fecha_vencimiento = ayer (exactamente 1 dia de atraso).
    Fail-closed: si la consulta falla, relanza la excepcion.
    """
    cliente_ids: Set[int] = set()
    cedulas: Set[str] = set()
    if db is None:
        return cliente_ids, cedulas
    hoy = fecha_referencia or hoy_negocio()
    fv_ayer = hoy - timedelta(days=1)
    rows = db.execute(
        select(Prestamo.cliente_id, Cliente.cedula)
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(
            Cuota.fecha_pago.is_(None),
            CUOTA_ESTADO_NO_PAGADA_PARA_NOTIF,
            Cuota.fecha_vencimiento == fv_ayer,
            SALDO_PENDIENTE_CUOTA > TOL_SALDO_CUOTA_NOTIFICACION,
            _prestamo_no_excluido_notif(),
            sql_cliente_sin_desistimiento(),
        )
        .distinct()
    ).all()
    for cid, ced in rows:
        if cid is None:
            continue
        cliente_ids.add(int(cid))
        ced_s = str(ced or "").strip()
        if ced_s:
            cedulas.add(ced_s)
    return cliente_ids, cedulas


def select_prestamos_prejudicial(
    db: Session, fecha_referencia: Optional[date] = None
) -> List[Tuple[int, int, int]]:
    """
    Prestamos «2 Cuotas»: >=2 cuotas impagas con atraso >= 1 dia.
    Incluye titulares que tambien califican en dia siguiente (se envian ambos).

    Returns list of (prestamo_id, cliente_id, total_cuotas_atrasadas).
    Fail-closed: propaga errores de BD.
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
        .where(*_where_cuota_atrasada_base(fv_max_atraso))
        .group_by(Prestamo.id, Prestamo.cliente_id)
        .having(func.count(Cuota.id) >= PREJUDICIAL_MIN_CUOTAS_CON_ATRASO_60)
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
    (cliente_ids, cedulas) de titulares en «2 Cuotas» (puede solapar dia siguiente).
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


def titulares_desde_items(items: List[dict]) -> Tuple[Set[int], Set[str]]:
    """cliente_ids y cedulas presentes en una lista de items de notificacion."""
    cliente_ids: Set[int] = set()
    cedulas: Set[str] = set()
    for item in items or []:
        if not isinstance(item, dict):
            continue
        cliente_id = item.get("cliente_id")
        try:
            if cliente_id is not None:
                cliente_ids.add(int(cliente_id))
        except (TypeError, ValueError):
            pass
        ced = str(item.get("cedula") or "").strip()
        if ced:
            cedulas.add(ced)
    return cliente_ids, cedulas


def filtrar_items_de_titulares(
    items: List[dict], cliente_ids: Set[int], cedulas: Set[str]
) -> List[dict]:
    """Deja solo items cuyo titular esta en cliente_ids o cedulas."""
    if not items:
        return items
    if not cliente_ids and not cedulas:
        return []
    return [it for it in items if _item_es_de_cliente(it, cliente_ids, cedulas)]


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


def filtrar_items_sin_dia_siguiente(
    db: Session,
    items: List[dict],
    fecha_referencia: Optional[date] = None,
    *,
    claves: Optional[Tuple[Set[int], Set[str]]] = None,
    etiqueta: str = "listado",
) -> List[dict]:
    """Quita de ``items`` los titulares que ya estan en dia siguiente."""
    if not items or db is None:
        return items
    if claves is None:
        claves = clientes_en_regla_dia_siguiente(db, fecha_referencia)
    cliente_ids, cedulas = claves
    if not cliente_ids and not cedulas:
        return items
    filtrados = [it for it in items if not _item_es_de_cliente(it, cliente_ids, cedulas)]
    omitidos = len(items) - len(filtrados)
    if omitidos:
        logger.info(
            "[notif_dedup] %s: %s item(s) omitidos por titular ya en dia siguiente",
            etiqueta,
            omitidos,
        )
    return filtrados


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


def item_excluido_por_dia_siguiente_en_envio(
    tipo: str,
    item: dict,
    cliente_ids: Set[int],
    cedulas: Set[str],
) -> bool:
    """True si este tipo+item no debe enviarse por exclusion con dia siguiente."""
    if (tipo or "").strip() not in TIPOS_EXCLUIDOS_SI_DIA_SIGUIENTE:
        return False
    return _item_es_de_cliente(item, cliente_ids, cedulas)


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


# --- COBRANZAS_EXCEL (modulo retirado en UI; no recorta segmentos activos) ---

TIPOS_EXCLUIDOS_SI_COBRANZAS_EXCEL = frozenset()


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
    """Modulo retirado."""
    if not items or db is None:
        return items
    return items


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


# --- CUOTAS_4_MAS (modulo retirado en UI; no recorta segmentos activos) ---

TIPOS_EXCLUIDOS_SI_CUOTAS_4_MAS = frozenset()


def filtrar_items_sin_cuotas_4_mas(
    db: Session,
    items: List[dict],
    fecha_referencia: Optional[date] = None,
    *,
    claves: Optional[Tuple[Set[int], Set[str]]] = None,
    etiqueta: str = "listado",
) -> List[dict]:
    """Modulo retirado."""
    if not items or db is None:
        return items
    return items


def item_excluido_por_cuotas_4_mas_en_envio(
    tipo: str,
    item: dict,
    cliente_ids: Set[int],
    cedulas: Set[str],
) -> bool:
    """True si este tipo+item no debe enviarse por exclusion mutua con CUOTAS_4_MAS."""
    if (tipo or "").strip() not in TIPOS_EXCLUIDOS_SI_CUOTAS_4_MAS:
        return False
    return _item_es_de_cliente_cobranzas(item, cliente_ids, cedulas)
