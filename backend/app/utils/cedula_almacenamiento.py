"""Normalizacion de cedula para almacenamiento: trim + mayusculas."""

from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session


def normalizar_cedula_almacenamiento(value: Optional[str]) -> Optional[str]:
    """Devuelve la cedula lista para persistir: strip + MAYUSCULAS. None si no hay valor."""
    if value is None:
        return None
    s = str(value).strip()
    return s.upper() if s else None


def alinear_cedulas_clientes_existentes(db: Session, cedulas: Iterable[Optional[str]]) -> None:
    """
    Pone clientes.cedula en mayusculas cuando coincide en mayusculas con la clave canonica.
    Evita violar fk_pagos_cedula al insertar pagos con cedula en mayusculas.
    """
    from app.models.cliente import Cliente

    norms = {str(c).strip().upper() for c in cedulas if c is not None and str(c).strip()}
    if not norms:
        return
    for cn in norms:
        rows = db.execute(select(Cliente).where(func.upper(Cliente.cedula) == cn)).scalars().all()
        for r in rows:
            if (r.cedula or "") != cn:
                r.cedula = cn
    db.flush()
