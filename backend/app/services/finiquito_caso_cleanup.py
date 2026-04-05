"""
Elimina filas en finiquito_casos cuando el préstamo deja de estar LIQUIDADO
(p. ej. vuelve a APROBADO por corrección de pagos/cuotas) o se edita el estado en otro módulo.
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models.finiquito import FiniquitoCaso
from app.services.finiquito_prestamo_gestion_sync import (
    limpiar_estado_gestion_finiquito_prestamos,
)

logger = logging.getLogger(__name__)


def eliminar_finiquito_casos_por_prestamo(db: Session, prestamo_id: int) -> int:
    """Borra todas las filas finiquito_casos vinculadas al préstamo. Retorna cantidad borrada."""
    pid = int(prestamo_id)
    n = (
        db.query(FiniquitoCaso)
        .filter(FiniquitoCaso.prestamo_id == pid)
        .delete(synchronize_session=False)
    )
    deleted = int(n or 0)
    limpiar_estado_gestion_finiquito_prestamos(db, [pid])
    if deleted:
        logger.info(
            "finiquito_cleanup: eliminados %s caso(s) finiquito prestamo_id=%s",
            deleted,
            prestamo_id,
        )
    return deleted


def eliminar_finiquito_casos_si_prestamo_no_liquidado(
    db: Session, prestamo_id: int, estado_prestamo: str | None
) -> int:
    """
    Si el préstamo no está en LIQUIDADO, elimina sus casos finiquito.
    Los casos materializados solo aplican a préstamos LIQUIDADO elegibles.
    """
    if (estado_prestamo or "").strip().upper() == "LIQUIDADO":
        return 0
    return eliminar_finiquito_casos_por_prestamo(db, prestamo_id)
