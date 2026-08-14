"""
Elimina pagos reportados de la cola (pendiente / en_revision).

Nunca borra filas de `pagos` ni `cuota_pagos`. El historial del reporte
cae por CASCADE. Acción irreversible sobre la fila de `pagos_reportados`.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.pago_reportado import PagoReportado

logger = logging.getLogger(__name__)

MAX_ELIMINAR_SELECCIONADOS = 80
ESTADOS_ELIMINABLES_COLA = frozenset({"pendiente", "en_revision"})


def eliminar_pagos_reportados_seleccionados(
    db: Session,
    ids: Sequence[int],
) -> Dict[str, Any]:
    """
    Borra hasta MAX_ELIMINAR_SELECCIONADOS reportes de cola.

    Omite ids inexistentes o con estado distinto de pendiente/en_revision
    (p. ej. importado/aprobado: el pago de cartera se conserva).
    """
    uniq = sorted({int(x) for x in ids if int(x) > 0})
    if not uniq:
        return {
            "ok": False,
            "eliminados": [],
            "omitidos": [],
            "mensaje": "Debe indicar al menos un pago reportado.",
        }
    if len(uniq) > MAX_ELIMINAR_SELECCIONADOS:
        return {
            "ok": False,
            "eliminados": [],
            "omitidos": [],
            "mensaje": (
                f"Máximo {MAX_ELIMINAR_SELECCIONADOS} reportes por lote."
            ),
        }

    rows = list(
        db.execute(select(PagoReportado).where(PagoReportado.id.in_(uniq)))
        .scalars()
        .all()
    )
    por_id = {int(r.id): r for r in rows}
    eliminados: List[Dict[str, Any]] = []
    omitidos: List[Dict[str, Any]] = []
    estados_previos: Dict[int, str] = {}

    for pid in uniq:
        pr = por_id.get(pid)
        if pr is None:
            omitidos.append({"id": pid, "motivo": "no_encontrado"})
            continue
        estado = (pr.estado or "").strip()
        if estado not in ESTADOS_ELIMINABLES_COLA:
            omitidos.append(
                {
                    "id": pid,
                    "motivo": "estado_no_eliminable",
                    "estado": estado,
                }
            )
            continue
        ref = (pr.referencia_interna or "").strip() or str(pid)
        estados_previos[pid] = estado
        db.delete(pr)
        eliminados.append({"id": pid, "referencia_interna": ref, "estado": estado})

    if eliminados:
        db.commit()
        logger.info(
            "[COBROS] eliminar-seleccionados n=%s ids=%s (pagos cartera no tocados)",
            len(eliminados),
            [x["id"] for x in eliminados],
        )

    n = len(eliminados)
    if n == 0:
        mensaje = "Ningún reporte de la cola se pudo eliminar."
    elif n == 1:
        mensaje = (
            f"Pago reportado {eliminados[0]['referencia_interna']} eliminado. "
            "Los pagos en cartera no se modificaron."
        )
    else:
        mensaje = (
            f"{n} pagos reportados eliminados. "
            "Los pagos en cartera no se modificaron."
        )
    return {
        "ok": n > 0,
        "eliminados": eliminados,
        "omitidos": omitidos,
        "estados_previos": estados_previos,
        "mensaje": mensaje,
    }
