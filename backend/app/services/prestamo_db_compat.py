# -*- coding: utf-8 -*-
"""Compatibilidad BD: columnas opcionales del modelo prestamos vs migraciones pendientes."""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import inspect
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_cached_fecha_liquidado: Optional[bool] = None


def reset_prestamos_fecha_liquidado_cache() -> None:
    """Para tests o tras aplicar migraciones en caliente (opcional)."""
    global _cached_fecha_liquidado
    _cached_fecha_liquidado = None


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
