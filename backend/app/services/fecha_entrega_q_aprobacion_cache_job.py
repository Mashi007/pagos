"""
Persiste en `prestamos.fecha_entrega_q_aprobacion_cache` la comparación columna Q (hoja) vs fecha_aprobacion.

Job programado (cada domingo 02:03 America/Caracas) y POST manual de refresco en notificaciones.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.prestamo import Prestamo
from app.services.comparar_fecha_entrega_q_aprobacion_service import (
    comparar_fecha_entrega_column_q_vs_aprobacion,
)

logger = logging.getLogger(__name__)

_EXCL = ("LIQUIDADO", "DESISTIMIENTO")


def ejecutar_refresh_fecha_entrega_q_aprobacion_cache_nightly(db: Session) -> Dict[str, Any]:
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
            comparar_fecha_entrega_column_q_vs_aprobacion(
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
                    "[fecha_q_cache_nightly] prestamo_id=%s cedula=%s: %s",
                    pid,
                    ced[:12],
                    e,
                )
    logger.info(
        "[fecha_q_cache_nightly] total_ids=%s ok=%s err=%s skipped=%s",
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
