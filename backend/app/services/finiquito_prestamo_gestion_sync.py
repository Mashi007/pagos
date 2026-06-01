"""
Refleja en prestamos.estado_gestion_finiquito la fase finiquito visible para todos
(REVISION, EN_PROCESO, TERMINADO). No sustituye prestamos.estado (LIQUIDADO, etc.).

En EN_PROCESO fija finiquito_tramite_fecha_limite al dia 30 del ciclo finiquito
(29 dias calendario despues de creado_en del caso, o hoy+29 si no hay caso). En otros estados la limpia.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Iterable

from sqlalchemy.orm import Session

from app.models.finiquito import FiniquitoCaso
from app.models.prestamo import Prestamo
from app.utils.dias_laborales_caracas import fecha_hoy_caracas

_PLAZO_CICLO_DIAS = 30
_VALORES_GESTION_EN_PRESTAMO = frozenset({"REVISION", "EN_PROCESO", "TERMINADO"})


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
        row = (
            db.query(FiniquitoCaso.creado_en)
            .filter(FiniquitoCaso.prestamo_id == int(prestamo_id))
            .order_by(FiniquitoCaso.id.desc())
            .first()
        )
        anchor: date
        if row and row[0] is not None:
            creado = row[0]
            anchor = creado.date() if isinstance(creado, datetime) else creado
        else:
            anchor = fecha_hoy_caracas()
        p.finiquito_tramite_fecha_limite = anchor + timedelta(days=_PLAZO_CICLO_DIAS - 1)
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
