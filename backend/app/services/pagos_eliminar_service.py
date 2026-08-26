# -*- coding: utf-8 -*-
"""
Elimina un pago de cartera y realinea cuotas.

- Espera a que termine cascada BG del mismo préstamo (evita locks ~40s).
- Mutex de eliminación: la cascada BG no arranca mientras borra filas.
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
    requiere_reset = False

    try:
        # Mutex primero: un POST/PUT concurrente ve eliminacion_activa y encola
        # requeue en vez de arrancar un hilo (o fallback sync) a mitad del DELETE.
        with eliminacion_context(prestamo_id_previo):
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

        # Fuera del mutex: iniciar_cascada veía eliminacion_activa y solo
        # marcaba requeue (HTTP 202 sin hilo → amortización a medias).
        if prestamo_id_previo:
            from app.services.revision_manual_cascada_bg import (
                get_status,
                iniciar_cascada_revision_manual,
            )

            st_after = get_status(db, int(prestamo_id_previo)) or {}
            need_cascada = requiere_reset or bool(st_after.get("requeue"))
            if need_cascada:
                cascada = iniciar_cascada_revision_manual(
                    db,
                    prestamo_id=int(prestamo_id_previo),
                    prestamo_ids=[int(prestamo_id_previo)],
                    pago_id=None,
                    current_user=current_user,
                    forzar_spawn=True,
                )
                token = cascada.get("token") or (cascada.get("estado") or {}).get(
                    "token"
                )
                logger.info(
                    "eliminar_pago pago_id=%s prestamo_id=%s: cascada BG tras delete "
                    "ok=%s token=%s requeue=%s",
                    pago_id,
                    prestamo_id_previo,
                    cascada.get("ok"),
                    token,
                    cascada.get("requeue"),
                )
                return {
                    "ok": True,
                    "pago_id": pago_id,
                    "prestamo_id": int(prestamo_id_previo),
                    "cascada_en_proceso": True,
                    "cascada_bg_token": token,
                    "cascada_requeue": bool(cascada.get("requeue")),
                    "mensaje": (
                        "Pago eliminado. La amortización se está reconstruyendo "
                        "en segundo plano."
                    ),
                }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        from app.services.pagos_aplicacion_prestamo import detalle_excepcion_db

        logger.error("Error eliminando pago %s: %s", pago_id, e)
        raise HTTPException(
            status_code=500,
            detail=f"Error al eliminar pago {pago_id}: {detalle_excepcion_db(e, max_len=400)}",
        ) from e

    return {
        "ok": True,
        "pago_id": pago_id,
        "prestamo_id": int(prestamo_id_previo) if prestamo_id_previo else None,
    }
