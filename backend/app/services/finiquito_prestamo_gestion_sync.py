"""
Refleja en prestamos.estado_gestion_finiquito la fase finiquito visible para todos
(REVISION, ACEPTADO, REVISION_CONTABLE, EN_PROCESO, TERMINADO). No sustituye
prestamos.estado (LIQUIDADO, etc.). RECHAZADO y estados desconocidos limpian la columna.

En EN_PROCESO fija finiquito_tramite_fecha_limite al dia 30 del ciclo finiquito
(29 dias calendario despues de creado_en del caso, o hoy+29 si no hay caso). En otros estados la limpia.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Iterable

from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.finiquito import FiniquitoCaso, FiniquitoEstadoHistorial
from app.models.prestamo import Prestamo
from app.utils.dias_laborales_caracas import fecha_hoy_caracas

_PLAZO_CICLO_DIAS = 30
_VALORES_GESTION_EN_PRESTAMO = frozenset(
    {
        "REVISION",
        "ACEPTADO",
        "REVISION_CONTABLE",
        "EN_PROCESO",
        "TERMINADO",
    }
)


def sincronizar_prestamo_estado_gestion_finiquito(
    db: Session, prestamo_id: int, finiquito_estado_caso: str | None
) -> None:
    """Actualiza o limpia columnas segun el estado actual del caso finiquito."""
    p = db.query(Prestamo).filter(Prestamo.id == int(prestamo_id)).first()
    if not p:
        return
    fe = (finiquito_estado_caso or "").strip().upper()
    if fe == "EN_PROCESO":
        p.estado_gestion_finiquito = "EN_PROCESO"
        row = (
            db.query(FiniquitoCaso.creado_en)
            .filter(FiniquitoCaso.prestamo_id == int(prestamo_id))
            .order_by(FiniquitoCaso.id.desc())
            .first()
        )
        anchor: date
        if row and row[0] is not None:
            creado = row[0]
            anchor = creado.date() if isinstance(creado, datetime) else creado
        else:
            anchor = fecha_hoy_caracas()
        p.finiquito_tramite_fecha_limite = anchor + timedelta(days=_PLAZO_CICLO_DIAS - 1)
    elif fe in _VALORES_GESTION_EN_PRESTAMO:
        p.estado_gestion_finiquito = fe
        p.finiquito_tramite_fecha_limite = None
    else:
        p.estado_gestion_finiquito = None
        p.finiquito_tramite_fecha_limite = None


def reconciliar_caso_y_prestamo_gestion_finiquito(
    db: Session,
    prestamo_id: int,
    *,
    promover_caso_a_trabajo: bool = False,
) -> Dict[str, Any]:
    """
    Corrige desfase prestamo.estado_gestion_finiquito vs finiquito_casos.estado.

    Por defecto el caso manda: si el prestamo quedo EN_PROCESO por error pero el caso
    sigue en REVISION/ACEPTADO (revision sin terminar), se baja el prestamo al caso.
    Solo con promover_caso_a_trabajo=True se sube el caso a EN_PROCESO.
    """
    pid = int(prestamo_id)
    p = db.query(Prestamo).filter(Prestamo.id == pid).first()
    c = db.query(FiniquitoCaso).filter(FiniquitoCaso.prestamo_id == pid).first()
    if not p or not c:
        return {
            "prestamo_id": pid,
            "ok": False,
            "accion": "omitido",
            "detalle": "sin prestamo o sin finiquito_caso",
        }

    est_p = (p.estado_gestion_finiquito or "").strip().upper()
    est_c = (c.estado or "").strip().upper()
    if est_p == est_c:
        return {
            "prestamo_id": pid,
            "caso_id": c.id,
            "ok": True,
            "accion": "ya_alineado",
            "estado": est_c,
        }

    if (
        promover_caso_a_trabajo
        and est_p == "EN_PROCESO"
        and est_c in ("REVISION", "ACEPTADO", "REVISION_CONTABLE")
    ):
        anterior = est_c
        c.estado = "EN_PROCESO"
        db.add(
            FiniquitoEstadoHistorial(
                caso_id=c.id,
                estado_anterior=anterior,
                estado_nuevo="EN_PROCESO",
                actor_tipo="sistema",
                user_id=None,
                nota="Reconciliacion explicita: caso promovido a EN_PROCESO.",
            )
        )
        sincronizar_prestamo_estado_gestion_finiquito(db, pid, "EN_PROCESO")
        return {
            "prestamo_id": pid,
            "caso_id": c.id,
            "ok": True,
            "accion": "caso_promovido_a_en_proceso",
            "estado_anterior": anterior,
            "estado_nuevo": "EN_PROCESO",
        }

    if est_p == "EN_PROCESO" and est_c in ("REVISION", "ACEPTADO", "REVISION_CONTABLE"):
        sincronizar_prestamo_estado_gestion_finiquito(db, pid, est_c)
        return {
            "prestamo_id": pid,
            "caso_id": c.id,
            "ok": True,
            "accion": "prestamo_bajado_a_caso",
            "estado_caso": est_c,
            "estado_prestamo_antes": est_p,
        }

    sincronizar_prestamo_estado_gestion_finiquito(db, pid, est_c or None)
    return {
        "prestamo_id": pid,
        "caso_id": c.id,
        "ok": True,
        "accion": "prestamo_alineado_a_caso",
        "estado_caso": est_c,
        "estado_prestamo_antes": est_p or None,
    }


def reconciliar_gestion_finiquito_por_cedula(
    db: Session,
    cedula: str,
    *,
    promover_caso_a_trabajo: bool = False,
) -> Dict[str, Any]:
    """Reconcilia todos los prestamos de una cedula con caso finiquito activo."""
    from sqlalchemy import func, select

    cedula_norm = (cedula or "").strip().upper()
    prestamo_ids = [
        int(r[0])
        for r in db.execute(
            select(Prestamo.id).where(
                func.upper(func.trim(Prestamo.cedula)) == cedula_norm
            )
        ).all()
    ]
    detalle = [
        reconciliar_caso_y_prestamo_gestion_finiquito(
            db, pid, promover_caso_a_trabajo=promover_caso_a_trabajo
        )
        for pid in prestamo_ids
    ]
    return {"cedula": cedula_norm, "prestamos": len(prestamo_ids), "detalle": detalle}


def limpiar_estado_gestion_finiquito_prestamos(
    db: Session, prestamo_ids: Iterable[int]
) -> None:
    """Pone NULL en varios prestamos (p. ej. al borrar casos finiquito)."""
    ids = sorted({int(x) for x in prestamo_ids if x is not None})
    if not ids:
        return
    db.query(Prestamo).filter(Prestamo.id.in_(ids)).update(
        {
            Prestamo.estado_gestion_finiquito: None,
            Prestamo.finiquito_tramite_fecha_limite: None,
        },
        synchronize_session=False,
    )
