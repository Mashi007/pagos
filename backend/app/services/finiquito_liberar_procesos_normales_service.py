"""
Sacar un caso finiquito y devolver el préstamo a cartera operativa (pagos, cuotas).

Usado cuando la conciliación confirma que el crédito no está realmente liquidado.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.finiquito import FiniquitoCaso
from app.models.prestamo import Prestamo
from app.models.revision_manual_conciliacion_reserva import RevisionManualConciliacionReserva
from app.services.finiquito_conciliacion_visto_service import purgar_reserva_conciliacion_caso
from app.services.finiquito_prestamo_gestion_sync import limpiar_estado_gestion_finiquito_prestamos
from app.services.prestamo_db_compat import prestamos_tiene_columna_fecha_liquidado

logger = logging.getLogger(__name__)

ESTADOS_CASO_LIBERAR_PROCESOS_NORMALES = frozenset({"REVISION", "ACEPTADO"})


def ejecutar_liberar_finiquito_a_procesos_normales(
    db: Session,
    caso_id: int,
) -> Dict[str, Any]:
    """
    - Solo REVISION (bandeja) o ACEPTADO (área revisión).
    - Purga reservas de conciliación.
    - Elimina finiquito_casos y limpia gestión finiquito en préstamo.
    - Alinea LIQUIDADO/APROBADO con cuotas; si sigue LIQUIDADO, fuerza APROBADO.
    """
    caso = db.query(FiniquitoCaso).filter(FiniquitoCaso.id == int(caso_id)).first()
    if not caso:
        return {"ok": False, "error": "Caso no encontrado", "http_status": 404}

    est_caso = (caso.estado or "").strip().upper()
    if est_caso not in ESTADOS_CASO_LIBERAR_PROCESOS_NORMALES:
        return {
            "ok": False,
            "error": (
                "Solo puede liberar a procesos normales desde la bandeja principal "
                "(Revision) o el area de revision (Validado)."
            ),
        }

    prestamo_id = int(caso.prestamo_id)
    purgar_reserva_conciliacion_caso(db, caso.id)

    r_rm = db.execute(
        delete(RevisionManualConciliacionReserva).where(
            RevisionManualConciliacionReserva.prestamo_id == prestamo_id
        )
    )
    reservas_rm = int(getattr(r_rm, "rowcount", 0) or 0)

    prestamo: Optional[Prestamo] = (
        db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
    )
    estado_antes = (prestamo.estado or "").strip().upper() if prestamo else ""

    db.delete(caso)
    limpiar_estado_gestion_finiquito_prestamos(db, [prestamo_id])
    db.flush()

    if prestamo:
        from app.services.pagos_cascada_aplicacion import (
            _marcar_prestamo_liquidado_si_corresponde,
        )

        _marcar_prestamo_liquidado_si_corresponde(prestamo_id, db)
        db.refresh(prestamo)

    estado_despues = (prestamo.estado or "").strip().upper() if prestamo else ""
    forzado_aprobado = False

    if prestamo and estado_despues in ("LIQUIDADO", "FINIQUITO"):
        prestamo.estado = "APROBADO"
        if prestamos_tiene_columna_fecha_liquidado(db):
            prestamo.fecha_liquidado = None
        estado_despues = "APROBADO"
        forzado_aprobado = True

    logger.info(
        "finiquito_liberar: caso_id=%s prestamo_id=%s estado %s -> %s forzado=%s reservas_rm=%s",
        caso_id,
        prestamo_id,
        estado_antes,
        estado_despues,
        forzado_aprobado,
        reservas_rm,
    )

    return {
        "ok": True,
        "prestamo_id": prestamo_id,
        "estado_prestamo_antes": estado_antes or None,
        "estado_prestamo_despues": estado_despues or None,
        "forzado_aprobado": forzado_aprobado,
        "reservas_revision_manual_purgadas": reservas_rm,
        "mensaje": (
            f"Préstamo #{prestamo_id} fuera del flujo finiquito; continúa en cartera "
            f"({estado_despues or 'sin cambio'})."
        ),
    }
