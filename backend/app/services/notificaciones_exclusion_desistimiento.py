# -*- coding: utf-8 -*-
"""
Regla critica de negocio para envios de notificaciones:

1) Por prestamo del item: NUNCA enviar si ese prestamo esta en LIQUIDADO o DESISTIMIENTO.
2) Por cliente: NUNCA enviar si el cliente tiene al menos un prestamo en DESISTIMIENTO
   (incluye masivos, cobranza, WhatsApp y correos aunque el item no traiga prestamo_id).

Comparacion de estados case-insensitive (trim + upper).

La exclusion en listados (query base) usa los mismos estados; este modulo es la red de
seguridad en el momento del envio (revalidar justo antes de send_email).
"""
from __future__ import annotations

import logging
from typing import Any, Optional, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.constants.prestamo_estados import (
    ESTADO_PRESTAMO_DESISTIMIENTO,
    ESTADOS_PRESTAMO_EXCLUIDOS_COBRANZA_NOTIF,
)
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo

logger = logging.getLogger(__name__)

_ESTADOS_BLOQUEO_PRESTAMO = tuple(ESTADOS_PRESTAMO_EXCLUIDOS_COBRANZA_NOTIF)


def _norm_estado(raw: Any) -> str:
    return str(raw or "").strip().upper()


def prestamo_bloqueado_para_notificacion(db: Session, prestamo_id: Optional[int]) -> bool:
    """
    True si el prestamo_id existe y su estado es LIQUIDADO o DESISTIMIENTO.
    Sin prestamo_id valido -> False (no se aplica este corte; puede aplicar el de cliente).
    """
    if prestamo_id is None:
        return False
    try:
        pid = int(prestamo_id)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    estado = db.scalar(select(Prestamo.estado).where(Prestamo.id == pid))
    return _norm_estado(estado) in { _norm_estado(e) for e in _ESTADOS_BLOQUEO_PRESTAMO }


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
    if est in { _norm_estado(e) for e in _ESTADOS_BLOQUEO_PRESTAMO }:
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
    if cliente_id is not None and int(cliente_id) > 0:
        return cliente_tiene_prestamo_desistimiento(db, int(cliente_id))

    ids: set[int] = set()
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

    return any(cliente_tiene_prestamo_desistimiento(db, cid) for cid in ids)


def item_bloqueado_para_envio_notificacion(
    db: Session, item: dict
) -> Tuple[bool, str]:
    """
    Corte unico al enviar un item de notificacion. NUNCA enviar si aplica.

    Orden:
    1) prestamo_id del item en LIQUIDADO o DESISTIMIENTO
    2) cliente_id (o cedula/email) con algun prestamo DESISTIMIENTO

    Returns (bloqueado, motivo_corto).
    """
    if not isinstance(item, dict):
        return False, ""
    pid = item.get("prestamo_id")
    motivo_p = motivo_bloqueo_prestamo_notificacion(db, pid)
    if motivo_p:
        return True, motivo_p
    cid = item.get("cliente_id")
    if cliente_tiene_prestamo_desistimiento(db, cid):
        return True, ESTADO_PRESTAMO_DESISTIMIENTO
    # Sin cliente_id: resolver por cedula/email (masivos / filas incompletas).
    try:
        cid_int = int(cid) if cid is not None else 0
    except (TypeError, ValueError):
        cid_int = 0
    if cid_int <= 0:
        if cliente_bloqueado_por_desistimiento(
            db,
            cliente_id=None,
            cedula=item.get("cedula"),
            email=(item.get("correo_1") or item.get("correo") or None),
        ):
            return True, ESTADO_PRESTAMO_DESISTIMIENTO
    return False, ""
