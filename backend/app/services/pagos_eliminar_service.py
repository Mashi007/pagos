# -*- coding: utf-8 -*-
"""
Elimina un pago de cartera y realinea cuotas.

- Espera a que termine cascada BG del mismo préstamo (evita locks ~40s).
- Mutex de eliminación: la cascada BG no arranca mientras borra filas.
- Advisory lock por préstamo (mismo que cascada) al mutar / realinear.
- Reintento ante DeadlockDetected (mismo patrón que reset_y_reaplicar).
- Si hace falta reset completo, lo encola en BG (HTTP 202) en lugar de bloquear el worker.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.pago import Pago
from app.services.pagos_eliminar_coordinacion import eliminacion_context

logger = logging.getLogger(__name__)


def ejecutar_eliminar_pago(
    db: Session,
    pago_id: int,
    *,
    current_user=None,
) -> Dict[str, Any]:
    """
    Borra el pago y dependencias. Devuelve dict con ok; si requiere cascada BG,
    incluye cascada_en_proceso, cascada_bg_token y prestamo_id.
    """
    row = db.get(Pago, pago_id)
    if not row:
        raise HTTPException(status_code=404, detail="Pago no encontrado")

    prestamo_id_previo = row.prestamo_id

    if prestamo_id_previo:
        from app.services.revision_manual_cascada_bg import (
            esperar_fin_cascada_bg,
            get_status,
            job_activo,
        )

        pid = int(prestamo_id_previo)
        st = get_status(db, pid) or {}
        if job_activo(pid) or st.get("en_proceso"):
            logger.info(
                "eliminar_pago pago_id=%s: esperando cascada BG prestamo_id=%s",
                pago_id,
                pid,
            )
            if not esperar_fin_cascada_bg(pid, max_espera_sec=600, poll_sec=1.0):
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Hay una cascada en segundo plano para este préstamo. "
                        "Espere a que termine e intente eliminar de nuevo."
                    ),
                )

    from app.core.db_transient import is_deadlock_error, run_with_deadlock_retry

    def _eliminar_once() -> Dict[str, Any]:
        return _ejecutar_eliminar_pago_once(db, pago_id, current_user=current_user)

    try:
        return run_with_deadlock_retry(
            db,
            _eliminar_once,
            attempts=3,
            log_prefix=f"[eliminar_pago pago={pago_id}]",
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        from app.services.pagos_aplicacion_prestamo import detalle_excepcion_db

        if is_deadlock_error(e):
            logger.error(
                "Error eliminando pago %s: deadlock agotado: %s", pago_id, e
            )
            raise HTTPException(
                status_code=500,
                detail=(
                    f"Error al eliminar pago {pago_id}: conflicto temporal "
                    f"(deadlock). Espere unos segundos e intente de nuevo. "
                    f"{detalle_excepcion_db(e, max_len=200)}"
                ),
            ) from e

        logger.error("Error eliminando pago %s: %s", pago_id, e)
        raise HTTPException(
            status_code=500,
            detail=f"Error al eliminar pago {pago_id}: {detalle_excepcion_db(e, max_len=400)}",
        ) from e


def _ejecutar_eliminar_pago_once(
    db: Session,
    pago_id: int,
    *,
    current_user=None,
) -> Dict[str, Any]:
    """
    Una pasada de delete + realinear.

    Re-lee el pago y re-adquiere el advisory lock (requerido tras rollback de
    deadlock retry).
    """
    from app.services.pagos_cascada_lock import adquirir_lock_cascada_prestamo

    row = db.get(Pago, pago_id)
    if not row:
        raise HTTPException(status_code=404, detail="Pago no encontrado")

    serial_previo = getattr(row, "numero_documento", None)
    prestamo_id_previo = row.prestamo_id

    with eliminacion_context(prestamo_id_previo):
        if prestamo_id_previo:
            adquirir_lock_cascada_prestamo(db, int(prestamo_id_previo))

        db.execute(
            text("DELETE FROM auditoria_conciliacion_manual WHERE pago_id = :pid"),
            {"pid": pago_id},
        )
        db.execute(
            text("DELETE FROM auditoria_pago_control5_visto WHERE pago_id = :pid"),
            {"pid": pago_id},
        )
        db.execute(text("DELETE FROM cuota_pagos WHERE pago_id = :pid"), {"pid": pago_id})
        db.execute(
            text("UPDATE cuotas SET pago_id = NULL WHERE pago_id = :pid"),
            {"pid": pago_id},
        )
        db.execute(text("DELETE FROM revisar_pagos WHERE pago_id = :pid"), {"pid": pago_id})

        db.delete(row)
        db.flush()
        from app.services.pago_numero_documento import (
            liberar_serial_tras_baja_o_cambio,
        )

        liberar_serial_tras_baja_o_cambio(db, serial_previo)

        requiere_reset = False
        if prestamo_id_previo:
            from app.services.pagos_cuotas_reaplicacion import (
                realinear_cuotas_prestamo_desde_cuota_pagos,
            )

            r = realinear_cuotas_prestamo_desde_cuota_pagos(db, int(prestamo_id_previo))
            if not r or not r.get("ok"):
                codigo = (r or {}).get("codigo")
                if codigo in (
                    "huella_duplicada",
                    "desistimiento",
                    "sin_pagos_elegibles",
                ) or (
                    "huella funcional" in str((r or {}).get("error") or "").lower()
                ) or (
                    "desistimiento" in str((r or {}).get("error") or "").lower()
                    or "liquidado" in str((r or {}).get("error") or "").lower()
                ):
                    logger.warning(
                        "eliminar_pago pago_id=%s: realinear bloqueado prestamo %s; "
                        "reintento liviano. detalle=%s",
                        pago_id,
                        prestamo_id_previo,
                        (r or {}).get("error"),
                    )
                    r2 = realinear_cuotas_prestamo_desde_cuota_pagos(
                        db, int(prestamo_id_previo)
                    )
                    if not r2.get("ok"):
                        raise HTTPException(
                            status_code=500,
                            detail=(
                                r2.get("error")
                                or "No se pudo realinear cuotas tras eliminar el pago"
                            )[:400],
                        )
                    requiere_reset = bool(r2.get("requiere_reset_cascada"))
                else:
                    raise HTTPException(
                        status_code=500,
                        detail=(
                            (r or {}).get("error")
                            or "No se pudo alinear cuotas tras eliminar el pago"
                        )[:400],
                    )
            else:
                requiere_reset = bool(r.get("requiere_reset_cascada"))

        db.commit()

        if prestamo_id_previo and requiere_reset:
            from app.services.revision_manual_cascada_bg import (
                iniciar_cascada_revision_manual,
            )

            cascada = iniciar_cascada_revision_manual(
                db,
                prestamo_id=int(prestamo_id_previo),
                prestamo_ids=[int(prestamo_id_previo)],
                pago_id=None,
                current_user=current_user,
            )
            logger.info(
                "eliminar_pago pago_id=%s prestamo_id=%s: cascada BG tras delete "
                "token=%s",
                pago_id,
                prestamo_id_previo,
                cascada.get("token"),
            )
            return {
                "ok": True,
                "pago_id": pago_id,
                "prestamo_id": int(prestamo_id_previo),
                "cascada_en_proceso": True,
                "cascada_bg_token": cascada.get("token"),
                "cascada_requeue": bool(cascada.get("requeue")),
                "mensaje": (
                    "Pago eliminado. La amortización se está reconstruyendo "
                    "en segundo plano."
                ),
            }

    return {
        "ok": True,
        "pago_id": pago_id,
        "prestamo_id": int(prestamo_id_previo) if prestamo_id_previo else None,
    }
