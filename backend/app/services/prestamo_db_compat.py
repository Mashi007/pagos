# -*- coding: utf-8 -*-
"""Compatibilidad BD: columnas opcionales del modelo prestamos vs migraciones pendientes."""

from __future__ import annotations

import logging
from datetime import date
from typing import Dict, List, Optional

from sqlalchemy import bindparam, inspect, text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_cached_fecha_liquidado: Optional[bool] = None
_cached_fecha_desistimiento: Optional[bool] = None


def reset_prestamos_fecha_liquidado_cache() -> None:
    """Para tests o tras aplicar migraciones en caliente (opcional)."""
    global _cached_fecha_liquidado, _cached_fecha_desistimiento
    _cached_fecha_liquidado = None
    _cached_fecha_desistimiento = None


def prestamos_tiene_columna_fecha_liquidado(db: Session) -> bool:
    """
    True si existe public.prestamos.fecha_liquidado (migracion 023).
    Cache por proceso: la primera sesion resuelve y se reutiliza.
    """
    global _cached_fecha_liquidado
    if _cached_fecha_liquidado is not None:
        return _cached_fecha_liquidado
    try:
        bind = db.get_bind()
        cols = inspect(bind).get_columns("prestamos")
        _cached_fecha_liquidado = any(
            c.get("name") == "fecha_liquidado" for c in cols
        )
    except Exception as e:
        logger.warning("prestamos_tiene_columna_fecha_liquidado: %s", e)
        _cached_fecha_liquidado = False
    return _cached_fecha_liquidado


def prestamos_tiene_columna_fecha_desistimiento(db: Session) -> bool:
    """True si existe public.prestamos.fecha_desistimiento (migracion 029)."""
    global _cached_fecha_desistimiento
    if _cached_fecha_desistimiento is not None:
        return _cached_fecha_desistimiento
    try:
        bind = db.get_bind()
        cols = inspect(bind).get_columns("prestamos")
        _cached_fecha_desistimiento = any(
            c.get("name") == "fecha_desistimiento" for c in cols
        )
    except Exception as e:
        logger.warning("prestamos_tiene_columna_fecha_desistimiento: %s", e)
        _cached_fecha_desistimiento = False
    return _cached_fecha_desistimiento


def fetch_prestamos_fecha_desistimiento_map(
    db: Session, ids: List[int]
) -> Dict[int, Optional[date]]:
    """id -> fecha_desistimiento (None si NULL en fila). Vacio si no hay columna o ids."""
    if not ids or not prestamos_tiene_columna_fecha_desistimiento(db):
        return {}
    uniq = list(dict.fromkeys(int(i) for i in ids))
    stmt = text("SELECT id, fecha_desistimiento FROM prestamos WHERE id IN :ids").bindparams(
        bindparam("ids", expanding=True)
    )
    out: Dict[int, Optional[date]] = {}
    for rid, fd in db.execute(stmt, {"ids": uniq}).all():
        if rid is not None:
            out[int(rid)] = fd
    return out
