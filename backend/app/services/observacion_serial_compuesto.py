"""Marca «Serial compuesto» en observaciones: no cuenta como caso a revisión manual."""
from __future__ import annotations

from typing import Any, Optional

MARCA_OBS_SERIAL_COMPUESTO = "Serial compuesto"
_LEGACY = ("serial mixto",)


def texto_tiene_marca_serial_compuesto(texto: Optional[str]) -> bool:
    d = (texto or "").strip().lower()
    if not d:
        return False
    if MARCA_OBS_SERIAL_COMPUESTO.lower() in d:
        return True
    return any(leg in d for leg in _LEGACY)


def observaciones_suprimen_caso_revision(*textos: Optional[str]) -> bool:
    """True si algún texto contiene la marca Serial compuesto (u alias legacy)."""
    for t in textos:
        if texto_tiene_marca_serial_compuesto(t):
            return True
    return False


def aplicar_supresion_revision_serial_compuesto(
    requiere_revision: bool, *textos: Optional[str]
) -> bool:
    """No enviar a cola revisión cuando la observación es serial compuesto."""
    if observaciones_suprimen_caso_revision(*textos):
        return False
    return requiere_revision


def sql_excluir_observacion_serial_compuesto(column) -> Any:
    """Predicado SQL: filas cuya observación NO contiene Serial compuesto."""
    from sqlalchemy import func, not_, or_

    obs = func.lower(func.coalesce(column, ""))
    return not_(
        or_(
            obs.like(f"%{MARCA_OBS_SERIAL_COMPUESTO.lower()}%"),
            obs.like("%serial mixto%"),
        )
    )
