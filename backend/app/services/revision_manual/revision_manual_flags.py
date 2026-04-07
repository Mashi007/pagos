"""Marcado en tabla revision_manual_prestamo tras mutaciones en préstamo/cuotas."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.revision_manual_prestamo import RevisionManualPrestamo


def marcar_o_crear_prestamo_editado_en_revision_manual(
    db: Session, prestamo_id: int
) -> None:
    """
    Marca prestamo_editado y actualizado_en. Si no hay fila de revisión, crea una en «revisando».
    Misma semántica que el bloque usado en PUT /revision-manual/prestamos/{id}.
    """
    rev_manual = (
        db.execute(
            select(RevisionManualPrestamo).where(
                RevisionManualPrestamo.prestamo_id == prestamo_id
            )
        )
        .scalars()
        .first()
    )
    now = datetime.now()
    if rev_manual:
        rev_manual.prestamo_editado = True
        rev_manual.actualizado_en = now
    else:
        db.add(
            RevisionManualPrestamo(
                prestamo_id=prestamo_id,
                estado_revision="revisando",
                prestamo_editado=True,
            )
        )


def marcar_prestamo_editado_si_existe_revision_manual(
    db: Session, prestamo_id: int
) -> None:
    """Solo actualiza flags si ya existe registro de revisión (no crea fila nueva)."""
    rev_manual = (
        db.execute(
            select(RevisionManualPrestamo).where(
                RevisionManualPrestamo.prestamo_id == prestamo_id
            )
        )
        .scalars()
        .first()
    )
    if not rev_manual:
        return
    rev_manual.prestamo_editado = True
    rev_manual.actualizado_en = datetime.now()
