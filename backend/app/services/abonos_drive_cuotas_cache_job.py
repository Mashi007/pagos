"""
Recalcula y persiste en `prestamos.abonos_drive_cuotas_cache` la comparación ABONOS (hoja) vs cuotas.

Ejecución prevista: cada domingo a las 04:35 America/Caracas (APScheduler, tras limpieza 04:00 y separado del job fecha Q), para la columna
«Diferencia abono» en Notificaciones > General (dato estático en listado hasta el siguiente cierre).
También se persiste al aplicar ABONOS desde la UI (ese préstamo).
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.prestamo import Prestamo
from app.services.comparar_abonos_drive_cuotas_service import comparar_abonos_drive_vs_cuotas

logger = logging.getLogger(__name__)

_EXCL = ("LIQUIDADO", "DESISTIMIENTO")


def ejecutar_refresh_abonos_drive_cuotas_cache_nightly(db: Session) -> Dict[str, Any]:
    """
    Recorre préstamos no liquidados/desistimiento y guarda el resultado de comparar (persist_cache=True).
    Hace commit por préstamo para no mantener una transacción enorme.
    """
    ok = 0
    err = 0
    skipped = 0
    ids = list(
        db.scalars(
            select(Prestamo.id)
            .where(~Prestamo.estado.in_(_EXCL))
            .order_by(Prestamo.id.asc())
        ).all()
    )
    total = len(ids)
    for pid in ids:
        p = db.get(Prestamo, int(pid))
        if p is None:
            skipped += 1
            continue
        ced = (p.cedula or "").strip()
        if not ced:
            skipped += 1
            continue
        try:
            comparar_abonos_drive_vs_cuotas(
                db,
                cedula=ced,
                prestamo_id=int(pid),
                lote=None,
                persist_cache=True,
            )
            db.commit()
            ok += 1
        except Exception as e:
            try:
                db.rollback()
            except Exception:
                pass
            err += 1
            if err <= 8:
                logger.warning(
                    "[abonos_drive_cache_nightly] prestamo_id=%s cedula=%s: %s",
                    pid,
                    ced[:12],
                    e,
                )
    logger.info(
        "[abonos_drive_cache_nightly] total_ids=%s ok=%s err=%s skipped=%s",
        total,
        ok,
        err,
        skipped,
    )
    return {
        "prestamos_considerados": total,
        "actualizados_ok": ok,
        "errores": err,
        "omitidos_sin_cedula": skipped,
    }
