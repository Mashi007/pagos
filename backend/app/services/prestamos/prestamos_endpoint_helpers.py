"""Helpers compartidos por el router de préstamos (escape ILIKE, resolución analista)."""

from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analista import Analista
from app.services.analistas_catalogo_sync import sincronizar_analistas_desde_prestamos_si_catalogo_vacio


def _escape_ilike_pattern(fragment: str) -> str:
    """Escape LIKE metacharacters for ILIKE with escape backslash (PostgreSQL)."""
    return fragment.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _resolver_analista_para_prestamo(
    db: Session,
    analista: Optional[str],
    analista_id: Optional[int],
) -> tuple[str, Optional[int]]:
    """
    Catálogo analistas: prioriza analista_id; si solo viene texto y existe en catálogo, enlaza id.
    Texto sin coincidencia se guarda en prestamos.analista sin id (cargas legacy / Excel).
    """
    sincronizar_analistas_desde_prestamos_si_catalogo_vacio(db)
    if analista_id is not None:
        row_a = db.get(Analista, analista_id)
        if not row_a:
            raise HTTPException(status_code=400, detail="analista_id no existe en el catálogo")
        if not row_a.activo:
            raise HTTPException(
                status_code=400,
                detail="El analista está inactivo; reactívelo en Analistas o elija otro.",
            )
        return row_a.nombre, row_a.id
    if analista is not None and str(analista).strip():
        n = str(analista).strip()
        found = db.execute(select(Analista).where(Analista.nombre == n)).scalar_one_or_none()
        if found:
            if not found.activo:
                raise HTTPException(
                    status_code=400,
                    detail="El analista está inactivo; reactívelo en Analistas o elija otro.",
                )
            return found.nombre, found.id
        return n, None
    return "", None
