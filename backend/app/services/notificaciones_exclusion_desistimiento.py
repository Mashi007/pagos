# -*- coding: utf-8 -*-
"""
Regla crítica de negocio: ningún envío de notificaciones a clientes que tengan
al menos un préstamo en estado DESISTIMIENTO (incluye masivos, cobranza, WhatsApp
y correos liquidado PDF si el cliente tiene desistimiento en cualquier operación).
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.prestamo import Prestamo

logger = logging.getLogger(__name__)


def cliente_tiene_prestamo_desistimiento(db: Session, cliente_id: Optional[int]) -> bool:
    """
    True si el cliente tiene al menos un préstamo con estado DESISTIMIENTO.
    Sin cliente_id válido → False (no se bloquea por esta regla).
    """
    if cliente_id is None or int(cliente_id) <= 0:
        return False
    n = db.scalar(
        select(func.count())
        .select_from(Prestamo)
        .where(
            Prestamo.cliente_id == int(cliente_id),
            Prestamo.estado == "DESISTIMIENTO",
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
    bloquea si el cliente (resuelto por id, cédula o email) tiene
    al menos un préstamo en DESISTIMIENTO.
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
            select(Cliente.id).where(func.lower(func.trim(Cliente.email)) == em)
        ).all()
        for r in rows:
            if r and r[0]:
                ids.add(int(r[0]))

    return any(cliente_tiene_prestamo_desistimiento(db, cid) for cid in ids)
