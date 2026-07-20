# -*- coding: utf-8 -*-
"""
Regla critica de negocio para envios de notificaciones:

1) Por prestamo del item: NUNCA enviar si ese prestamo esta en LIQUIDADO o DESISTIMIENTO.
2) Por cliente: NUNCA enviar si el cliente tiene al menos un prestamo en DESISTIMIENTO
   (incluye masivos, cobranza, WhatsApp y correos aunque el item no traiga prestamo_id).
3) Por cliente: NUNCA enviar si el cliente solo tiene prestamos LIQUIDADO/DESISTIMIENTO
   (sin cartera activa): persona liquidada / desistida.

Comparacion de estados case-insensitive (trim + upper).

La exclusion en listados (query base) usa los mismos estados; este modulo es la red de
seguridad en el momento del envio (revalidar justo antes de send_email).
"""
from __future__ import annotations

import logging
from typing import Any, Optional, Set, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, aliased

from app.constants.prestamo_estados import (
    ESTADO_PRESTAMO_DESISTIMIENTO,
    ESTADOS_PRESTAMO_EXCLUIDOS_COBRANZA_NOTIF,
)
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo

logger = logging.getLogger(__name__)

_ESTADOS_BLOQUEO_PRESTAMO = tuple(ESTADOS_PRESTAMO_EXCLUIDOS_COBRANZA_NOTIF)
_ESTADOS_BLOQUEO_SET = {str(e).strip().upper() for e in _ESTADOS_BLOQUEO_PRESTAMO}


def _norm_estado(raw: Any) -> str:
    return str(raw or "").strip().upper()


def prestamo_bloqueado_para_notificacion(db: Session, prestamo_id: Optional[int]) -> bool:
    """
    True si el prestamo_id existe y su estado es LIQUIDADO o DESISTIMIENTO.
    Sin prestamo_id valido -> False (no se aplica este corte; puede aplicar el de cliente).
    """
    return motivo_bloqueo_prestamo_notificacion(db, prestamo_id) is not None


def motivo_bloqueo_prestamo_notificacion(db: Session, prestamo_id: Optional[int]) -> Optional[str]:
    """Devuelve el estado bloqueante del prestamo o None."""
    if prestamo_id is None:
        return None
    try:
        pid = int(prestamo_id)
    except (TypeError, ValueError):
        return None
    if pid <= 0:
        return None
    estado = db.scalar(select(Prestamo.estado).where(Prestamo.id == pid))
    est = _norm_estado(estado)
    if est in _ESTADOS_BLOQUEO_SET:
        return est
    return None


def cliente_tiene_prestamo_desistimiento(db: Session, cliente_id: Optional[int]) -> bool:
    """
    True si el cliente tiene al menos un prestamo con estado DESISTIMIENTO
    (comparacion case-insensitive).
    Sin cliente_id valido -> False (no se bloquea por esta regla).
    """
    if cliente_id is None:
        return False
    try:
        cid = int(cliente_id)
    except (TypeError, ValueError):
        return False
    if cid <= 0:
        return False
    estado_norm = func.upper(func.trim(func.coalesce(Prestamo.estado, "")))
    n = db.scalar(
        select(func.count())
        .select_from(Prestamo)
        .where(
            Prestamo.cliente_id == cid,
            estado_norm == str(ESTADO_PRESTAMO_DESISTIMIENTO).strip().upper(),
        )
    )
    return (n or 0) > 0


def cliente_sin_cartera_activa_notif(db: Session, cliente_id: Optional[int]) -> bool:
    """
    True si el cliente tiene al menos un prestamo y ninguno esta fuera de
    LIQUIDADO/DESISTIMIENTO (persona liquidada / sin credito activo).
    Sin prestamos -> False (no se bloquea por esta regla; masivos sin cartera).
    """
    if cliente_id is None:
        return False
    try:
        cid = int(cliente_id)
    except (TypeError, ValueError):
        return False
    if cid <= 0:
        return False
    estado_norm = func.upper(func.trim(func.coalesce(Prestamo.estado, "")))
    total = db.scalar(
        select(func.count()).select_from(Prestamo).where(Prestamo.cliente_id == cid)
    )
    if not total:
        return False
    activos = db.scalar(
        select(func.count())
        .select_from(Prestamo)
        .where(
            Prestamo.cliente_id == cid,
            estado_norm.notin_(tuple(_ESTADOS_BLOQUEO_SET)),
        )
    )
    return (activos or 0) == 0


def motivo_bloqueo_cliente_notif(db: Session, cliente_id: Optional[int]) -> Optional[str]:
    """
    Motivo de bloqueo a nivel cliente, o None.
    Prioridad: DESISTIMIENTO (cualquier prestamo) > LIQUIDADO (solo cartera excluida).
    """
    if cliente_tiene_prestamo_desistimiento(db, cliente_id):
        return ESTADO_PRESTAMO_DESISTIMIENTO
    if cliente_sin_cartera_activa_notif(db, cliente_id):
        return "LIQUIDADO"
    return None


def _resolver_cliente_ids(
    db: Session,
    cliente_id: Optional[int] = None,
    cedula: Optional[str] = None,
    email: Optional[str] = None,
) -> Set[int]:
    ids: set[int] = set()
    if cliente_id is not None:
        try:
            cid = int(cliente_id)
        except (TypeError, ValueError):
            cid = 0
        if cid > 0:
            ids.add(cid)
            return ids

    ced = (cedula or "").strip()
    if ced:
        row = db.execute(select(Cliente.id).where(Cliente.cedula == ced)).first()
        if row and row[0]:
            ids.add(int(row[0]))

    em = (email or "").strip().lower()
    if em:
        rows = db.execute(
            select(Cliente.id).where(
                or_(
                    func.lower(func.trim(Cliente.email)) == em,
                    func.lower(func.trim(func.coalesce(Cliente.email_secundario, ""))) == em,
                )
            )
        ).all()
        for r in rows:
            if r and r[0]:
                ids.add(int(r[0]))
    return ids


def cliente_bloqueado_por_desistimiento(
    db: Session,
    cliente_id: Optional[int] = None,
    cedula: Optional[str] = None,
    email: Optional[str] = None,
) -> bool:
    """
    Regla global para correos al cliente:
    bloquea si el cliente (resuelto por id, cedula o email) tiene
    al menos un prestamo en DESISTIMIENTO.
    """
    ids = _resolver_cliente_ids(db, cliente_id=cliente_id, cedula=cedula, email=email)
    return any(cliente_tiene_prestamo_desistimiento(db, cid) for cid in ids)


def cliente_bloqueado_para_notificacion(
    db: Session,
    cliente_id: Optional[int] = None,
    cedula: Optional[str] = None,
    email: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Bloqueo a nivel persona: DESISTIMIENTO (cualquier prestamo) o sin cartera activa
    (solo LIQUIDADO/DESISTIMIENTO). Returns (bloqueado, motivo).
    """
    ids = _resolver_cliente_ids(db, cliente_id=cliente_id, cedula=cedula, email=email)
    for cid in ids:
        motivo = motivo_bloqueo_cliente_notif(db, cid)
        if motivo:
            return True, motivo
    return False, ""


def sql_cliente_sin_desistimiento():
    """
    Clausula SQLAlchemy: Prestamo.cliente_id no tiene ningun prestamo DESISTIMIENTO.
    Usar en queries de listados de cobranza/notificaciones.
    """
    p_des = aliased(Prestamo)
    estado_norm = func.upper(func.trim(func.coalesce(p_des.estado, "")))
    subq = (
        select(p_des.cliente_id)
        .where(
            estado_norm == str(ESTADO_PRESTAMO_DESISTIMIENTO).strip().upper(),
            p_des.cliente_id.isnot(None),
        )
        .distinct()
    )
    return ~Prestamo.cliente_id.in_(subq)


def item_bloqueado_para_envio_notificacion(
    db: Session, item: dict
) -> Tuple[bool, str]:
    """
    Corte unico al enviar un item de notificacion. NUNCA enviar si aplica.

    Orden:
    1) prestamo_id del item en LIQUIDADO o DESISTIMIENTO
    2) cliente_id (o cedula/email) con DESISTIMIENTO o sin cartera activa (solo LIQUIDADO)

    Returns (bloqueado, motivo_corto).
    """
    if not isinstance(item, dict):
        return False, ""
    pid = item.get("prestamo_id")
    motivo_p = motivo_bloqueo_prestamo_notificacion(db, pid)
    if motivo_p:
        return True, motivo_p

    cid = item.get("cliente_id")
    try:
        cid_int = int(cid) if cid is not None else 0
    except (TypeError, ValueError):
        cid_int = 0

    if cid_int > 0:
        motivo_c = motivo_bloqueo_cliente_notif(db, cid_int)
        if motivo_c:
            return True, motivo_c
        return False, ""

    bloqueado, motivo = cliente_bloqueado_para_notificacion(
        db,
        cliente_id=None,
        cedula=item.get("cedula"),
        email=(item.get("correo_1") or item.get("correo") or None),
    )
    if bloqueado:
        return True, motivo
    return False, ""
