"""
Refresco de finiquito_casos: antes de materializar, persiste como LIQUIDADO los
préstamos APROBADO que ya están efectivamente cubiertos por cuotas. Luego toma
solo préstamos LIQUIDADO donde la suma de cuotas.total_pagado cuadra con
total_financiamiento con tolerancia 0.02 (alineado con redondeos y cuadre
pagos/cuotas en cartera).

- Jobs lun-sab 01:00 y 13:00 America/Caracas (si ENABLE_AUTOMATIC_SCHEDULED_JOBS).
- Tras marcar LIQUIDADO en cascada de pagos/cuotas: refrescar un solo préstamo
  (refrescar_finiquito_caso_prestamo_si_aplica), sin depender del cron.
"""
import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import insert, text
from sqlalchemy.orm import Session

from app.models.finiquito import FiniquitoCaso, FiniquitoEstadoHistorial
from app.services.finiquito_caso_cleanup import eliminar_finiquito_casos_por_prestamo
from app.services.finiquito_db_schema import finiquito_casos_has_contacto_para_siguientes
from app.services.finiquito_prestamo_gestion_sync import (
    limpiar_estado_gestion_finiquito_prestamos,
)

logger = logging.getLogger(__name__)

ESTADO_ENTRADA_TRABAJO = "ACEPTADO"


def persistir_liquidaciones_efectivas_para_finiquito(db: Session) -> None:
    """
    Alinea la liquidacion efectiva que ya muestra la UI con el estado persistido.

    La funcion SQL existente actualiza prestamos APROBADO con todas las cuotas
    cubiertas a LIQUIDADO y registra auditoria_cambios_estado_prestamo. No hace
    commit aqui: el refresco de finiquitos controla la transaccion completa.
    """
    db.execute(text("SELECT actualizar_prestamos_a_liquidado_automatico()"))


def _es_revision_heredada_sin_gestion(db: Session, caso: FiniquitoCaso) -> bool:
    """True si el caso quedo en REVISION por la regla anterior, no por decision operativa."""
    if (caso.estado or "").strip().upper() != "REVISION":
        return False
    tiene_historial = (
        db.query(FiniquitoEstadoHistorial.id)
        .filter(FiniquitoEstadoHistorial.caso_id == int(caso.id))
        .first()
        is not None
    )
    return not tiene_historial


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
        if _es_revision_heredada_sin_gestion(db, caso_existente):
            caso_existente.estado = ESTADO_ENTRADA_TRABAJO
        return "actualizado"
    if finiquito_casos_has_contacto_para_siguientes(db):
        db.add(
            FiniquitoCaso(
                prestamo_id=pid,
                cliente_id=cliente_id,
                cedula=cedula,
                total_financiamiento=total_fin,
                sum_total_pagado=sum_tp,
                estado=ESTADO_ENTRADA_TRABAJO,
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
                estado=ESTADO_ENTRADA_TRABAJO,
                ultimo_refresh_utc=now,
            )
        )
    return "insertado"


def refrescar_finiquito_caso_prestamo_si_aplica(db: Session, prestamo_id: int) -> dict[str, Any]:
    """
    Alinea finiquito_casos para un solo prestamo con la misma regla que el refresco masivo.

    No hace commit: el llamador controla la transaccion (p. ej. aplicar pago a cuotas).
    Si el préstamo no califica (no LIQUIDADO o suma fuera de tolerancia respecto a
    total_financiamiento), elimina filas finiquito de ese préstamo y limpia
    estado_gestion_finiquito en préstamos.
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
        HAVING ABS(
            COALESCE(SUM(COALESCE(c.total_pagado, 0)), 0) - COALESCE(p.total_financiamiento, 0)
        ) <= 0.02
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
    - Inserta nuevos casos en ACEPTADO (area de trabajo) para prestamos LIQUIDADO que cumplen la regla.
    - Actualiza sum_total_pagado / totales en casos existentes.
      Si aun estaban en REVISION por la regla anterior y no tienen historial operativo,
      los normaliza a ACEPTADO.
    - Elimina casos cuyo prestamo ya no califica (dejo de ser LIQUIDADO, cuotas sin cuadrar, etc.),
      en cualquier estado del caso (REVISION, ACEPTADO, area de trabajo, etc.).
    """
    persistir_liquidaciones_efectivas_para_finiquito(db)

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
        HAVING ABS(
            COALESCE(SUM(COALESCE(c.total_pagado, 0)), 0) - COALESCE(p.total_financiamiento, 0)
        ) <= 0.02
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
