"""
Evita borrar casos finiquito por efectos colaterales (conciliar, refresh, cascada).

Los casos en bandejas posteriores a la entrada o con conciliación en curso solo deben
salir del flujo por acciones voluntarias del panel (validar, pasar a trabajo, rechazar, eliminar).
"""
from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.finiquito import FiniquitoCaso
from app.models.revision_manual_conciliacion_reserva import RevisionManualConciliacionReserva

logger = logging.getLogger(__name__)

# Posterior a bandeja principal (REVISION): no auto-eliminar por LIQUIDADO temporal.
ESTADOS_CASO_PROTEGIDOS_AUTO_LIMPIEZA = frozenset(
    {"ACEPTADO", "REVISION_CONTABLE", "EN_PROCESO", "TERMINADO", "RECHAZADO"}
)


def prestamo_tiene_reserva_revision_manual_conciliacion_activa(
    db: Session, prestamo_id: int
) -> bool:
    """Conciliar en revisión manual dejó reserva temporal antes de recrear pagos."""
    n = int(
        db.scalar(
            select(func.count())
            .select_from(RevisionManualConciliacionReserva)
            .where(RevisionManualConciliacionReserva.prestamo_id == int(prestamo_id))
        )
        or 0
    )
    return n > 0


def prestamo_tiene_finiquito_caso_protegido(db: Session, prestamo_id: int) -> bool:
    """True si el préstamo no debe perder su caso finiquito por limpieza automática."""
    pid = int(prestamo_id)
    caso = db.query(FiniquitoCaso).filter(FiniquitoCaso.prestamo_id == pid).first()
    if caso and (caso.estado or "").strip().upper() in ESTADOS_CASO_PROTEGIDOS_AUTO_LIMPIEZA:
        return True

    from app.services.finiquito_conciliacion_visto_service import (
        prestamo_tiene_reserva_finiquito_activa,
    )

    if prestamo_tiene_reserva_finiquito_activa(db, pid):
        return True
    if prestamo_tiene_reserva_revision_manual_conciliacion_activa(db, pid):
        return True
    return False


def prestamo_ids_finiquito_protegidos_contra_auto_limpieza(db: Session) -> set[int]:
    """Conjunto de prestamo_id que el refresh masivo no debe borrar."""
    ids: set[int] = set()
    for (pid,) in (
        db.query(FiniquitoCaso.prestamo_id)
        .filter(FiniquitoCaso.estado.in_(tuple(ESTADOS_CASO_PROTEGIDOS_AUTO_LIMPIEZA)))
        .distinct()
        .all()
    ):
        if pid is not None:
            ids.add(int(pid))

    from app.services.finiquito_conciliacion_visto_service import (
        prestamo_ids_conciliacion_visto_protegidos,
    )

    ids.update(prestamo_ids_conciliacion_visto_protegidos(db))

    for (pid,) in db.execute(
        select(RevisionManualConciliacionReserva.prestamo_id).distinct()
    ).all():
        if pid is not None:
            ids.add(int(pid))

    return ids
