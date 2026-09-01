"""Filtros del listado operativo de préstamos (Lista de Préstamos)."""
from __future__ import annotations

from sqlalchemy import or_, select, true
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.models.prestamo import Prestamo
from app.services.prestamos.cupo_cedula_aprobados import (
    claves_cedula_con_n_aprobados_en_cartera,
)
from app.utils.cedula_almacenamiento import expr_cedula_normalizada_para_comparar


def condicion_prestamo_listado_sin_cedula_duplicada(
    db: Session,
    *,
    min_prestamos: int = 2,
) -> ColumnElement[bool]:
    """
    Excluye cédulas con ``min_prestamos`` o más préstamos **APROBADO** (misma regla que cupo).

    LIQUIDADO + 1 APROBADO sí aparece en lista (renovación). Solo se oculta 2+ APROBADO duplicado.
    """
    dup = claves_cedula_con_n_aprobados_en_cartera(db, min_aprobados=min_prestamos)
    if not dup:
        return true()
    ced = expr_cedula_normalizada_para_comparar(Prestamo.cedula)
    return or_(ced == "", ced.is_(None), ~ced.in_(sorted(dup)))
