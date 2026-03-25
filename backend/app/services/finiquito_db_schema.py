"""Inspeccion de esquema finiquito (compatibilidad si aun no se aplico migracion 025)."""

from __future__ import annotations

import logging
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_cols_by_bind: dict[int, frozenset[str]] = {}
_audit_by_bind: dict[int, bool] = {}


def _bind_key(db: Session) -> int:
    return id(db.get_bind())


def finiquito_casos_column_names(db: Session) -> frozenset[str]:
    bid = _bind_key(db)
    if bid in _cols_by_bind:
        return _cols_by_bind[bid]
    try:
        cols = frozenset(
            c["name"] for c in sa_inspect(db.get_bind()).get_columns("finiquito_casos")
        )
    except Exception as e:
        logger.warning("finiquito_db_schema: no se pudieron leer columnas de finiquito_casos: %s", e)
        cols = frozenset()
    _cols_by_bind[bid] = cols
    return cols


def finiquito_casos_has_contacto_para_siguientes(db: Session) -> bool:
    return "contacto_para_siguientes" in finiquito_casos_column_names(db)


def finiquito_has_area_trabajo_auditoria_table(db: Session) -> bool:
    bid = _bind_key(db)
    if bid in _audit_by_bind:
        return _audit_by_bind[bid]
    try:
        ok = bool(sa_inspect(db.get_bind()).has_table("finiquito_area_trabajo_auditoria"))
    except Exception as e:
        logger.warning("finiquito_db_schema: has_table auditoria: %s", e)
        ok = False
    _audit_by_bind[bid] = ok
    return ok


def clear_finiquito_schema_cache() -> None:
    """Tests o tras migraciones en caliente (raro)."""
    _cols_by_bind.clear()
    _audit_by_bind.clear()
