"""
Refresco de finiquito_casos: prestamos donde sum(cuotas.total_pagado) = total_financiamiento
(comparacion exacta en SQL). Invocado por scheduler 02:00 America/Caracas.
"""
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import insert, text
from sqlalchemy.orm import Session

from app.models.finiquito import FiniquitoCaso
from app.services.finiquito_db_schema import finiquito_casos_has_contacto_para_siguientes

logger = logging.getLogger(__name__)


def ejecutar_refresh_finiquito_casos(db: Session) -> dict[str, Any]:
    """
    - Inserta nuevos casos en REVISION.
    - Actualiza sum_total_pagado / totales en casos existentes (mantiene estado).
    - Elimina casos cuyo prestamo ya no cumple la regla.
    """
    sql = text(
        """
        SELECT p.id AS prestamo_id,
               p.cliente_id,
               TRIM(p.cedula) AS cedula,
               p.total_financiamiento,
               COALESCE(SUM(COALESCE(c.total_pagado, 0)), 0) AS sum_tp
        FROM prestamos p
        INNER JOIN cuotas c ON c.prestamo_id = p.id
        GROUP BY p.id, p.cliente_id, p.cedula, p.total_financiamiento
        HAVING COALESCE(SUM(COALESCE(c.total_pagado, 0)), 0) = p.total_financiamiento
        """
    )
    rows = db.execute(sql).fetchall()
    now = datetime.utcnow()
    qualifying_ids = [int(r[0]) for r in rows]

    insertados = 0
    actualizados = 0

    if not qualifying_ids:
        eliminados = db.query(FiniquitoCaso).delete(synchronize_session=False)
        db.commit()
        logger.info(
            "finiquito_refresh: sin prestamos elegibles; eliminados=%s",
            eliminados,
        )
        return {
            "elegibles": 0,
            "insertados": 0,
            "actualizados": 0,
            "eliminados": eliminados,
        }

    existentes_list = (
        db.query(FiniquitoCaso).filter(FiniquitoCaso.prestamo_id.in_(qualifying_ids)).all()
    )
    por_prestamo = {c.prestamo_id: c for c in existentes_list}

    for r in rows:
        prestamo_id = int(r[0])
        cliente_id = r[1]
        cedula = (r[2] or "").strip()
        total_fin = r[3]
        sum_tp = r[4]

        if prestamo_id in por_prestamo:
            caso = por_prestamo[prestamo_id]
            caso.cliente_id = cliente_id
            caso.cedula = cedula
            caso.total_financiamiento = total_fin
            caso.sum_total_pagado = sum_tp
            caso.ultimo_refresh_utc = now
            actualizados += 1
        else:
            if finiquito_casos_has_contacto_para_siguientes(db):
                db.add(
                    FiniquitoCaso(
                        prestamo_id=prestamo_id,
                        cliente_id=cliente_id,
                        cedula=cedula,
                        total_financiamiento=total_fin,
                        sum_total_pagado=sum_tp,
                        estado="REVISION",
                        ultimo_refresh_utc=now,
                    )
                )
            else:
                db.execute(
                    insert(FiniquitoCaso.__table__).values(
                        prestamo_id=prestamo_id,
                        cliente_id=cliente_id,
                        cedula=cedula,
                        total_financiamiento=total_fin,
                        sum_total_pagado=sum_tp,
                        estado="REVISION",
                        ultimo_refresh_utc=now,
                    )
                )
            insertados += 1

    # No borrar casos ya aceptados o en flujo de area de trabajo (evita perder auditoria).
    eliminados = (
        db.query(FiniquitoCaso)
        .filter(
            ~FiniquitoCaso.prestamo_id.in_(qualifying_ids),
            ~FiniquitoCaso.estado.in_(["ACEPTADO", "EN_PROCESO", "TERMINADO"]),
        )
        .delete(synchronize_session=False)
    )

    db.commit()
    logger.info(
        "finiquito_refresh: elegibles=%s insertados=%s actualizados=%s eliminados=%s",
        len(qualifying_ids),
        insertados,
        actualizados,
        eliminados,
    )
    return {
        "elegibles": len(qualifying_ids),
        "insertados": insertados,
        "actualizados": actualizados,
        "eliminados": eliminados,
    }
