# -*- coding: utf-8 -*-
"""
Catch-up de pagos operativos sin articulación completa en cuota_pagos.

Solo prestamos APROBADO (no toca LIQUIDADO/DESISTIMIENTO: eso es remediación staff).
Lote acotado + advisory lock para no saturar BD ni solapar workers.

Usado por cron (ENABLE_CRON_PAGOS_HUERFANOS_CATCHUP) y ejecutable a mano:
  python -m app.services.pagos_huerfanos_catchup_job
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import SessionLocal

logger = logging.getLogger(__name__)

JOB_LOCK_KEY = 931338
DEFAULT_BATCH = 80

_SQL_CANDIDATOS = """
SELECT DISTINCT p.prestamo_id
FROM pagos p
JOIN prestamos pr ON pr.id = p.prestamo_id
WHERE pr.estado = 'APROBADO'
  AND p.prestamo_id IS NOT NULL
  AND p.monto_pagado > 0
  AND NOT (
    UPPER(COALESCE(p.estado, '')) IN (
      'ANULADO_IMPORT', 'DUPLICADO', 'CANCELADO', 'RECHAZADO', 'REVERSADO'
    )
    OR UPPER(COALESCE(p.estado, '')) LIKE '%%ANUL%%'
    OR UPPER(COALESCE(p.estado, '')) LIKE '%%REVERS%%'
    OR LOWER(COALESCE(p.estado, '')) IN ('cancelado', 'rechazado')
  )
  AND (
    NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = p.id)
    OR COALESCE((
         SELECT SUM(cp2.monto_aplicado) FROM cuota_pagos cp2 WHERE cp2.pago_id = p.id
       ), 0) < (p.monto_pagado::numeric - 0.02)
  )
  AND EXISTS (
    SELECT 1
    FROM cuotas c
    WHERE c.prestamo_id = p.prestamo_id
      AND UPPER(TRIM(COALESCE(c.estado, ''))) IN ('PENDIENTE', 'VENCIDO', 'MORA', 'PARCIAL')
      AND (COALESCE(c.monto, 0) - COALESCE(c.total_pagado, 0)) > 0.01
  )
ORDER BY p.prestamo_id
LIMIT :lim
"""


def listar_prestamo_ids_huerfanos_aprobado(db: Session, *, limit: int = DEFAULT_BATCH) -> list[int]:
    lim = max(1, min(int(limit or DEFAULT_BATCH), 500))
    rows = db.execute(text(_SQL_CANDIDATOS), {"lim": lim}).fetchall()
    return [int(r[0]) for r in rows if r and r[0] is not None]


def ejecutar_catchup_huerfanos_aprobado(
    db: Session,
    *,
    limit: int = DEFAULT_BATCH,
    usar_lock: bool = True,
) -> dict[str, Any]:
    """
    Por cada prestamo APROBADO candidato:
    1) aplicar_pagos_pendientes_prestamo (incremental)
    2) si sigue requiriendo correccion, reset_y_reaplicar_cascada_prestamo
    Un commit por prestamo ok.
    """
    lock_acquired = False
    if usar_lock:
        lock_acquired = bool(
            db.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": JOB_LOCK_KEY}).scalar()
        )
        if not lock_acquired:
            logger.info("catchup huerfanos omitido: otra instancia tiene el lock")
            return {
                "omitido_por_lock": True,
                "candidatos": 0,
                "ok_incremental": 0,
                "ok_cascada": 0,
                "errores": 0,
            }

    from app.api.v1.endpoints.pagos import aplicar_pagos_pendientes_prestamo
    from app.services.pagos_cuotas_reaplicacion import (
        prestamo_requiere_correccion_cascada,
        reset_y_reaplicar_cascada_prestamo,
    )

    ids = listar_prestamo_ids_huerfanos_aprobado(db, limit=limit)
    ok_inc = 0
    ok_casc = 0
    err = 0
    detalle_err: list[dict[str, Any]] = []

    try:
        for pid in ids:
            try:
                n = aplicar_pagos_pendientes_prestamo(pid, db)
                if n > 0:
                    db.commit()
                    ok_inc += 1
                else:
                    db.rollback()

                if prestamo_requiere_correccion_cascada(db, pid):
                    r = reset_y_reaplicar_cascada_prestamo(db, pid)
                    if r.get("ok"):
                        db.commit()
                        ok_casc += 1
                        logger.info(
                            "catchup huerfanos cascada ok prestamo_id=%s pagos=%s",
                            pid,
                            r.get("pagos_reaplicados"),
                        )
                    else:
                        db.rollback()
                        err += 1
                        detalle_err.append(
                            {"prestamo_id": pid, "error": r.get("error") or "cascada"}
                        )
                        logger.warning(
                            "catchup huerfanos cascada fail prestamo_id=%s err=%s",
                            pid,
                            r.get("error"),
                        )
            except Exception as e:
                db.rollback()
                err += 1
                detalle_err.append({"prestamo_id": pid, "error": str(e)[:300]})
                logger.exception("catchup huerfanos prestamo_id=%s: %s", pid, e)
    finally:
        if lock_acquired:
            try:
                db.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": JOB_LOCK_KEY})
                db.commit()
            except Exception:
                logger.exception("catchup huerfanos: no se pudo liberar advisory lock")

    out = {
        "omitido_por_lock": False,
        "candidatos": len(ids),
        "ok_incremental": ok_inc,
        "ok_cascada": ok_casc,
        "errores": err,
        "errores_detalle": detalle_err[:20],
    }
    logger.info(
        "catchup huerfanos fin candidatos=%s ok_inc=%s ok_casc=%s err=%s",
        out["candidatos"],
        ok_inc,
        ok_casc,
        err,
    )
    return out


def job_catchup_huerfanos_aprobado_scheduler() -> None:
    from app.core.config import settings

    if not getattr(settings, "ENABLE_CRON_PAGOS_HUERFANOS_CATCHUP", True):
        return
    lim = int(getattr(settings, "CRON_PAGOS_HUERFANOS_CATCHUP_BATCH", DEFAULT_BATCH) or DEFAULT_BATCH)
    db = SessionLocal()
    try:
        ejecutar_catchup_huerfanos_aprobado(db, limit=lim, usar_lock=True)
    except Exception:
        logger.exception("job catchup huerfanos APROBADO fallo")
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _db = SessionLocal()
    try:
        print(ejecutar_catchup_huerfanos_aprobado(_db, limit=DEFAULT_BATCH))
    finally:
        _db.close()
