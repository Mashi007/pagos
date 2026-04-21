"""
Persiste en `prestamos.fecha_entrega_q_aprobacion_cache` la comparación columna Q (hoja) vs fecha_aprobacion.

- Tras cada sync exitoso de la hoja CONCILIACIÓN (Drive → `conciliacion_sheet_*`), el API dispara la misma pasada
  masiva para que listados y auditoría vuelvan a leer la Q frente a la BD con el snapshot nuevo.
- Job programado: lunes y jueves 04:00 America/Caracas (si `ENABLE_FECHA_ENTREGA_Q_CACHE_NIGHTLY` y scheduler activo).
- POST manual `/notificaciones/refresh-fecha-entrega-q-cache` (misma función `ejecutar_refresh_fecha_entrega_q_aprobacion_cache_nightly`).
- Ámbito: todos los préstamos con cédula en BD (sin excluir LIQUIDADO, DESISTIMIENTO ni otro estado).
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


def ejecutar_refresh_fecha_entrega_q_aprobacion_cache_nightly(db: Session) -> Dict[str, Any]:
    """
    Recalcula caché Q vs aprobación para **todos** los préstamos con cédula (sin excluir por estado:
    LIQUIDADO, DESISTIMIENTO, etc. entran igual; coherente con auditoría /notificaciones/fecha-q-auditoria-total).
    """
    ok = 0
    err = 0
    skipped = 0
    ids = list(
        db.scalars(
            select(Prestamo.id).order_by(Prestamo.id.asc())
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


def ejecutar_refresh_fecha_entrega_q_cache_tras_sync_conciliacion(db: Session) -> Dict[str, Any]:
    """
    Invocado inmediatamente después de un sync exitoso CONCILIACIÓN (Google Sheets → BD).
    Misma pasada que el job programado / el POST de refresco manual.
    """
    logger.info(
        "[fecha_q_cache] Refresco masivo por sincronización Drive (conciliacion_sheet → comparación Q vs BD)"
    )
    return ejecutar_refresh_fecha_entrega_q_aprobacion_cache_nightly(db)
