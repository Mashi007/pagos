"""
Refleja en prestamos.estado_gestion_finiquito la fase finiquito visible para todos
(ANTIGUO, EN_PROCESO, TERMINADO). No sustituye prestamos.estado (LIQUIDADO, etc.).

En EN_PROCESO fija finiquito_tramite_fecha_limite = 15 dias laborales (lun-vie,
America/Caracas) desde la fecha del cambio. En otros estados la limpia.
"""
from __future__ import annotations

from typing import Iterable

from sqlalchemy.orm import Session

from app.models.prestamo import Prestamo
from app.utils.dias_laborales_caracas import (
    fecha_hoy_caracas,
    sumar_dias_laborales_lun_vie,
)

_VALORES_GESTION_EN_PRESTAMO = frozenset({"ANTIGUO", "EN_PROCESO", "TERMINADO"})


def sincronizar_prestamo_estado_gestion_finiquito(
    db: Session, prestamo_id: int, finiquito_estado_caso: str | None
) -> None:
    """Actualiza o limpia columnas segun el estado actual del caso finiquito."""
    p = db.query(Prestamo).filter(Prestamo.id == int(prestamo_id)).first()
    if not p:
        return
    fe = (finiquito_estado_caso or "").strip().upper()
    if fe == "EN_PROCESO":
        p.estado_gestion_finiquito = "EN_PROCESO"
        anchor = fecha_hoy_caracas()
        p.finiquito_tramite_fecha_limite = sumar_dias_laborales_lun_vie(anchor, 15)
    elif fe in _VALORES_GESTION_EN_PRESTAMO:
        p.estado_gestion_finiquito = fe
        p.finiquito_tramite_fecha_limite = None
    else:
        p.estado_gestion_finiquito = None
        p.finiquito_tramite_fecha_limite = None


def limpiar_estado_gestion_finiquito_prestamos(
    db: Session, prestamo_ids: Iterable[int]
) -> None:
    """Pone NULL en varios prestamos (p. ej. al borrar casos finiquito)."""
    ids = sorted({int(x) for x in prestamo_ids if x is not None})
    if not ids:
        return
    db.query(Prestamo).filter(Prestamo.id.in_(ids)).update(
        {
            Prestamo.estado_gestion_finiquito: None,
            Prestamo.finiquito_tramite_fecha_limite: None,
        },
        synchronize_session=False,
    )
