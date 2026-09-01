"""Filtros del listado operativo de préstamos (Lista de Préstamos)."""
from __future__ import annotations

from sqlalchemy import or_, select, true
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.models.prestamo import Prestamo
from app.services.prestamos.cupo_cedula_aprobados import (
    claves_cedula_cupo_aprobado_excedido_en_cartera,
)
from app.utils.cedula_almacenamiento import expr_cedula_normalizada_para_comparar


def condicion_prestamo_listado_sin_cedula_duplicada(
    db: Session,
    *,
    min_prestamos: int = 2,
) -> ColumnElement[bool]:
    """
    Excluye cédulas que **exceden cupo** APROBADO: V/E con 2+ (max 1), J con varios OK.

    LIQUIDADO + 1 APROBADO sí aparece (renovación). J503848898 con 3 APROBADO no se oculta.
    """
    dup = claves_cedula_cupo_aprobado_excedido_en_cartera(db)
    if not dup:
        return true()
    ced = expr_cedula_normalizada_para_comparar(Prestamo.cedula)
    return or_(ced == "", ced.is_(None), ~ced.in_(sorted(dup)))
