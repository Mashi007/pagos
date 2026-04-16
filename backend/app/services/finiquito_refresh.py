"""
Refresco de finiquito_casos: solo prestamos en estado LIQUIDADO donde
sum(cuotas.total_pagado) = total_financiamiento (comparacion exacta en SQL).
Nota: el marcado LIQUIDADO en pagos usa tolerancia 0.01 por cuota; si por redondeo
la suma de total_pagado no iguala exactamente total_financiamiento, no habra fila
finiquito hasta corregir cuotas o ejecutar criterio manual / ajuste futuro de tolerancia.

- Job diario 02:00 America/Caracas (si ENABLE_AUTOMATIC_SCHEDULED_JOBS).
- Tras marcar LIQUIDADO en cascada de pagos/cuotas: refrescar un solo prestamo
  (refrescar_finiquito_caso_prestamo_si_aplica), sin depender del cron.
"""
import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import insert, text
from sqlalchemy.orm import Session

from app.models.finiquito import FiniquitoCaso
from app.services.finiquito_caso_cleanup import eliminar_finiquito_casos_por_prestamo
from app.services.finiquito_db_schema import finiquito_casos_has_contacto_para_siguientes
from app.services.finiquito_prestamo_gestion_sync import (
    limpiar_estado_gestion_finiquito_prestamos,
)

logger = logging.getLogger(__name__)


def _upsert_finiquito_caso_desde_valores(
    db: Session,
    *,
    prestamo_id: int,
    cliente_id: Any,
    cedula: str,
    total_fin: Any,
    sum_tp: Any,
    now: datetime,
    caso_existente: Optional[FiniquitoCaso],
) -> str:
    """Inserta o actualiza un FiniquitoCaso; retorna 'insertado' o 'actualizado'. No hace commit."""
    pid = int(prestamo_id)
    if caso_existente:
        caso_existente.cliente_id = cliente_id
        caso_existente.cedula = cedula
        caso_existente.total_financiamiento = total_fin
        caso_existente.sum_total_pagado = sum_tp
        caso_existente.ultimo_refresh_utc = now
        return "actualizado"
    if finiquito_casos_has_contacto_para_siguientes(db):
        db.add(
            FiniquitoCaso(
                prestamo_id=pid,
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
                prestamo_id=pid,
                cliente_id=cliente_id,
                cedula=cedula,
                total_financiamiento=total_fin,
                sum_total_pagado=sum_tp,
                estado="REVISION",
                ultimo_refresh_utc=now,
            )
        )
    return "insertado"


def refrescar_finiquito_caso_prestamo_si_aplica(db: Session, prestamo_id: int) -> dict[str, Any]:
    """
    Alinea finiquito_casos para un solo prestamo con la misma regla que el refresco masivo.

    No hace commit: el llamador controla la transaccion (p. ej. aplicar pago a cuotas).
    Si el prestamo no califica (no LIQUIDADO o suma distinta de total_financiamiento),
    elimina filas finiquito de ese prestamo y limpia estado_gestion_finiquito en prestamos.
    """
    pid = int(prestamo_id)
    # Misma sesion que marco LIQUIDADO en ORM: asegurar que el SELECT raw ve el estado persistido.
    db.flush()

    sql = text(
        """
        SELECT p.id AS prestamo_id,
               p.cliente_id,
               TRIM(p.cedula) AS cedula,
               p.total_financiamiento,
               COALESCE(SUM(COALESCE(c.total_pagado, 0)), 0) AS sum_tp
        FROM prestamos p
        INNER JOIN cuotas c ON c.prestamo_id = p.id
        WHERE p.id = :pid
          AND UPPER(TRIM(COALESCE(p.estado, ''))) = 'LIQUIDADO'
        GROUP BY p.id, p.cliente_id, p.cedula, p.total_financiamiento
        HAVING COALESCE(SUM(COALESCE(c.total_pagado, 0)), 0) = p.total_financiamiento
        """
    )
    row = db.execute(sql, {"pid": pid}).fetchone()
    now = datetime.utcnow()

    if not row:
        deleted = eliminar_finiquito_casos_por_prestamo(db, pid)
        out: dict[str, Any] = {
            "prestamo_id": pid,
            "accion": "eliminado" if deleted else "sin_cambio",
            "filas_borradas": int(deleted or 0),
        }
        if deleted:
            logger.info("finiquito_refresh(prestamo): no elegible; %s", out)
        else:
            logger.debug("finiquito_refresh(prestamo): no elegible sin filas finiquito; %s", out)
        return out

    cliente_id = row[1]
    cedula = (row[2] or "").strip()
    total_fin = row[3]
    sum_tp = row[4]

    caso = (
        db.query(FiniquitoCaso).filter(FiniquitoCaso.prestamo_id == pid).first()
    )
    accion = _upsert_finiquito_caso_desde_valores(
        db,
        prestamo_id=pid,
        cliente_id=cliente_id,
        cedula=cedula,
        total_fin=total_fin,
        sum_tp=sum_tp,
        now=now,
        caso_existente=caso,
    )

    logger.info(
        "finiquito_refresh(prestamo): prestamo_id=%s accion=%s sum_tp=%s total_fin=%s",
        pid,
        accion,
        sum_tp,
        total_fin,
    )
    return {
        "prestamo_id": pid,
        "accion": accion,
        "sum_total_pagado": str(sum_tp) if sum_tp is not None else None,
        "total_financiamiento": str(total_fin) if total_fin is not None else None,
    }


def ejecutar_refresh_finiquito_casos(db: Session) -> dict[str, Any]:
    """
    - Inserta nuevos casos en REVISION (solo prestamos LIQUIDADO que cumplen la regla).
    - Actualiza sum_total_pagado / totales en casos existentes (mantiene estado).
    - Elimina casos cuyo prestamo ya no califica (dejo de ser LIQUIDADO, cuotas sin cuadrar, etc.),
      en cualquier estado del caso (REVISION, ACEPTADO, area de trabajo, etc.).
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
        WHERE UPPER(TRIM(COALESCE(p.estado, ''))) = 'LIQUIDADO'
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
        pids_borrar = [
            int(r[0])
            for r in db.query(FiniquitoCaso.prestamo_id).distinct().all()
        ]
        limpiar_estado_gestion_finiquito_prestamos(db, pids_borrar)
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

        caso = por_prestamo.get(prestamo_id)
        acc = _upsert_finiquito_caso_desde_valores(
            db,
            prestamo_id=prestamo_id,
            cliente_id=cliente_id,
            cedula=cedula,
            total_fin=total_fin,
            sum_tp=sum_tp,
            now=now,
            caso_existente=caso,
        )
        if acc == "actualizado":
            actualizados += 1
        else:
            insertados += 1

    pids_borrar = [
        int(r[0])
        for r in db.query(FiniquitoCaso.prestamo_id)
        .filter(~FiniquitoCaso.prestamo_id.in_(qualifying_ids))
        .distinct()
        .all()
    ]
    limpiar_estado_gestion_finiquito_prestamos(db, pids_borrar)
    eliminados = (
        db.query(FiniquitoCaso)
        .filter(~FiniquitoCaso.prestamo_id.in_(qualifying_ids))
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
