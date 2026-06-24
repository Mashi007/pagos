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
import time
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.prestamo import Prestamo
from app.services.comparar_fecha_entrega_q_aprobacion_service import (
    ConciliacionSheetLookupContext,
    comparar_fecha_entrega_column_q_vs_aprobacion,
    prestamo_fecha_q_cache_vigente_y_alineado,
)

logger = logging.getLogger(__name__)

# Commits cada N préstamos (menos round-trips que commit por fila).
_LOTE_COMMIT = 100
# Log de progreso cada N préstamos procesados (no cada fila).
_LOG_PROGRESO_CADA = 250


def ejecutar_refresh_fecha_entrega_q_aprobacion_cache_nightly(db: Session) -> Dict[str, Any]:
    """
    Recalcula caché Q vs aprobación para **todos** los préstamos con cédula (sin excluir por estado:
    LIQUIDADO, DESISTIMIENTO, etc. entran igual; coherente con auditoría /notificaciones/fecha-q-auditoria-total).
    """
    t0 = time.perf_counter()
    ok = 0
    err = 0
    skipped = 0
    omitidos_cache_vigente = 0
    aplicables = 0
    lote_commit = 0
    pendientes_commit = 0

    ids = list(
        db.scalars(select(Prestamo.id).order_by(Prestamo.id.asc())).all()
    )
    total = len(ids)
    sheet_lookup = ConciliacionSheetLookupContext.build_from_db(db)
    meta_synced_at = sheet_lookup.meta_synced_at

    logger.info(
        "[fecha_q_cache_nightly] inicio total_ids=%s filas_hoja_indexadas=%s",
        total,
        sheet_lookup.total_filas_hoja_indexadas,
    )

    for idx, pid in enumerate(ids, start=1):
        p = db.get(Prestamo, int(pid))
        if p is None:
            skipped += 1
            continue
        ced = (p.cedula or "").strip()
        if not ced:
            skipped += 1
            continue

        if prestamo_fecha_q_cache_vigente_y_alineado(p, meta_synced_at):
            omitidos_cache_vigente += 1
            continue

        try:
            out = comparar_fecha_entrega_column_q_vs_aprobacion(
                db,
                cedula=ced,
                prestamo_id=int(pid),
                lote=None,
                persist_cache=True,
                sheet_lookup=sheet_lookup,
                lote_indice=(idx - 1) // _LOTE_COMMIT + 1,
            )
            if out.get("puede_aplicar"):
                aplicables += 1
            ok += 1
            pendientes_commit += 1
            if pendientes_commit >= _LOTE_COMMIT:
                db.commit()
                lote_commit += 1
                pendientes_commit = 0
                logger.info(
                    "[fecha_q_cache_nightly] lote_commit=%s progreso=%s/%s ok=%s err=%s "
                    "omitidos_cache=%s aplicables=%s",
                    lote_commit,
                    idx,
                    total,
                    ok,
                    err,
                    omitidos_cache_vigente,
                    aplicables,
                )
        except Exception as e:
            try:
                db.rollback()
            except Exception:
                pass
            err += 1
            pendientes_commit = 0
            if err <= 8:
                logger.warning(
                    "[fecha_q_cache_nightly] prestamo_id=%s cedula=%s: %s",
                    pid,
                    ced[:12],
                    e,
                )

        if idx % _LOG_PROGRESO_CADA == 0 and pendientes_commit > 0:
            logger.info(
                "[fecha_q_cache_nightly] progreso=%s/%s ok=%s err=%s omitidos_cache=%s aplicables=%s",
                idx,
                total,
                ok,
                err,
                omitidos_cache_vigente,
                aplicables,
            )

    if pendientes_commit > 0:
        db.commit()
        lote_commit += 1

    duracion_s = round(time.perf_counter() - t0, 2)
    logger.info(
        "[fecha_q_cache_nightly] fin total_ids=%s ok=%s err=%s skipped=%s "
        "omitidos_cache_vigente=%s aplicables=%s lotes_commit=%s duracion_s=%s",
        total,
        ok,
        err,
        skipped,
        omitidos_cache_vigente,
        aplicables,
        lote_commit,
        duracion_s,
    )
    return {
        "prestamos_considerados": total,
        "actualizados_ok": ok,
        "errores": err,
        "omitidos_sin_cedula": skipped,
        "omitidos_cache_vigente": omitidos_cache_vigente,
        "con_puede_aplicar": aplicables,
        "lotes_commit": lote_commit,
        "duracion_s": duracion_s,
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


def ejecutar_refresh_fecha_entrega_q_cache_background() -> None:
    """
    Ejecuta el refresco masivo en un hilo de BackgroundTasks (sesión propia).
    Usado tras POST /conciliacion-sheet/sync y /sync-now para no bloquear la respuesta HTTP.
    """
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        logger.info(
            "[fecha_q_cache] inicio refresco en segundo plano (post-sync CONCILIACIÓN)"
        )
        res = ejecutar_refresh_fecha_entrega_q_aprobacion_cache_nightly(db)
        logger.info("[fecha_q_cache] fin refresco background resultado=%s", res)
    except Exception:
        logger.exception("[fecha_q_cache] error en refresco background")
    finally:
        db.close()
