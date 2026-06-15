"""
Detecta y corrige duplicados en cédulas V/E (máximo un APROBADO).

Reglas de producto:
- **J**: puede tener uno o más créditos (no aplica borrado automático por duplicado).
- **V/E**: a lo sumo un préstamo APROBADO; LIQUIDADO no cuenta para el cupo.

Borrado (solo V/E, sin pagos):
1) Re-importe: mismo crédito ya LIQUIDADO (misma huella operativa).
2) Más de un APROBADO en la misma cédula: sobrantes con cero pagos (se conserva el de menor id).
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import and_, exists, func, not_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.constants.prestamo_estados import ESTADO_PRESTAMO_DESISTIMIENTO
from app.models.cuota import Cuota
from app.models.cuota_pago import CuotaPago
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.services.prestamo_candidatos_drive_validadores import cedula_cmp_es_tipo_v_o_e
from app.services.prestamos.prestamo_eliminacion import eliminar_prestamo_por_id
from app.services.prestamos.prestamo_huella import (
    normalizar_cedula_huella,
    normalizar_modalidad_producto,
)

logger = logging.getLogger(__name__)

_MOTIVO_GUARDAR = (
    "ya existe un préstamo LIQUIDADO con la misma huella (cédula, fechas, monto, "
    "cuotas y modalidad); no se permite re-importar desde Drive."
)

_NOTA_OBS_DESISTIMIENTO = (
    "[AUTO] Duplicado re-importe Drive: mismo crédito ya LIQUIDADO sin pagos en este préstamo."
)


def _fecha_aprobacion_date(prestamo: Prestamo) -> Optional[date]:
    fa = getattr(prestamo, "fecha_aprobacion", None)
    if fa is None:
        return None
    if isinstance(fa, datetime):
        return fa.date()
    if isinstance(fa, date):
        return fa
    return None


def _cedula_norm_expr():
    return func.btrim(func.upper(Prestamo.cedula))


def _filtro_cedula_ve_sql():
    ced = _cedula_norm_expr()
    return or_(ced.like("V%"), ced.like("E%"))


def cedula_aplica_tope_un_aprobado(cedula: str | None) -> bool:
    """True para cédulas V o E (máximo un APROBADO activo)."""
    return cedula_cmp_es_tipo_v_o_e(normalizar_cedula_huella(cedula or ""))


def existe_liquidado_misma_huella_operativa(
    db: Session,
    *,
    cedula: str | None,
    fecha_aprobacion: date | None,
    fecha_requerimiento: date | None,
    total_financiamiento: Decimal | None,
    numero_cuotas: int | None,
    modalidad_pago: str | None,
    exclude_prestamo_id: int | None = None,
) -> bool:
    if not cedula_aplica_tope_un_aprobado(cedula):
        return False
    if (
        not (cedula or "").strip()
        or fecha_aprobacion is None
        or fecha_requerimiento is None
        or total_financiamiento is None
        or numero_cuotas is None
        or not (modalidad_pago or "").strip()
    ):
        return False

    cedula_n = normalizar_cedula_huella(cedula)
    modalidad_n = normalizar_modalidad_producto(modalidad_pago)

    cond = [
        Prestamo.estado == "LIQUIDADO",
        _cedula_norm_expr() == cedula_n,
        Prestamo.fecha_requerimiento == fecha_requerimiento,
        Prestamo.total_financiamiento == total_financiamiento,
        Prestamo.numero_cuotas == int(numero_cuotas),
        func.btrim(func.upper(Prestamo.modalidad_pago)) == modalidad_n,
        func.date(Prestamo.fecha_aprobacion) == fecha_aprobacion,
    ]
    if exclude_prestamo_id is not None:
        cond.append(Prestamo.id != int(exclude_prestamo_id))

    n = int(db.scalar(select(func.count()).select_from(Prestamo).where(*cond)) or 0)
    return n > 0


def existe_liquidado_misma_huella_operativa_prestamo(
    db: Session,
    prestamo: Prestamo,
    *,
    exclude_prestamo_id: int | None = None,
) -> bool:
    return existe_liquidado_misma_huella_operativa(
        db,
        cedula=prestamo.cedula,
        fecha_aprobacion=_fecha_aprobacion_date(prestamo),
        fecha_requerimiento=prestamo.fecha_requerimiento,
        total_financiamiento=prestamo.total_financiamiento,
        numero_cuotas=prestamo.numero_cuotas,
        modalidad_pago=prestamo.modalidad_pago,
        exclude_prestamo_id=exclude_prestamo_id,
    )


def ensure_no_reimporte_liquidado_huella(
    db: Session,
    prestamo: Prestamo,
    *,
    exclude_prestamo_id: int | None = None,
) -> None:
    """HTTP 409 si cédula V/E y ya existe LIQUIDADO con la misma huella operativa."""
    if not cedula_aplica_tope_un_aprobado(prestamo.cedula):
        return
    if existe_liquidado_misma_huella_operativa_prestamo(
        db, prestamo, exclude_prestamo_id=exclude_prestamo_id
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Ya existe un prestamo LIQUIDADO con la misma huella operativa "
                "(cedula, fecha aprobacion, fecha requerimiento, monto, cuotas y modalidad). "
                "No se permite duplicar el credito."
            ),
        )


def motivo_si_reimporte_liquidado_desde_fechas(
    db: Session,
    *,
    cedula: str,
    fecha_aprobacion: date,
    fecha_requerimiento: date,
    total_financiamiento: Decimal,
    numero_cuotas: int,
    modalidad_pago: str,
) -> Optional[str]:
    if not cedula_aplica_tope_un_aprobado(cedula):
        return None
    if existe_liquidado_misma_huella_operativa(
        db,
        cedula=cedula,
        fecha_aprobacion=fecha_aprobacion,
        fecha_requerimiento=fecha_requerimiento,
        total_financiamiento=total_financiamiento,
        numero_cuotas=numero_cuotas,
        modalidad_pago=modalidad_pago,
    ):
        return _MOTIVO_GUARDAR
    return None


def prestamo_tiene_pagos_o_aplicaciones_cuota(db: Session, prestamo_id: int) -> bool:
    pid = int(prestamo_id)
    n_pagos = int(
        db.scalar(select(func.count()).select_from(Pago).where(Pago.prestamo_id == pid)) or 0
    )
    if n_pagos > 0:
        return True
    n_cp = int(
        db.scalar(
            select(func.count())
            .select_from(CuotaPago)
            .join(Cuota, Cuota.id == CuotaPago.cuota_id)
            .where(Cuota.prestamo_id == pid)
        )
        or 0
    )
    return n_cp > 0


def _estado_borrable_duplicado(estado: str | None, observaciones: str | None) -> bool:
    est = (estado or "").strip().upper()
    if est == "APROBADO":
        return True
    if est == ESTADO_PRESTAMO_DESISTIMIENTO:
        obs = (observaciones or "").strip()
        return _NOTA_OBS_DESISTIMIENTO in obs
    return False


def _id_aprobado_menor_misma_cedula(db: Session, cedula: str | None) -> Optional[int]:
    cedula_n = normalizar_cedula_huella(cedula or "")
    if not cedula_n:
        return None
    val = db.scalar(
        select(func.min(Prestamo.id)).where(
            Prestamo.estado == "APROBADO",
            _cedula_norm_expr() == cedula_n,
        )
    )
    return int(val) if val is not None else None


def _motivo_borrado_ve(db: Session, row: Prestamo) -> Optional[str]:
    """
    None si no debe borrarse. Solo cédulas V/E sin pagos.
    """
    if not cedula_aplica_tope_un_aprobado(row.cedula):
        return None
    if not _estado_borrable_duplicado(row.estado, row.observaciones):
        return None
    if prestamo_tiene_pagos_o_aplicaciones_cuota(db, int(row.id)):
        return None

    if existe_liquidado_misma_huella_operativa_prestamo(
        db, row, exclude_prestamo_id=int(row.id)
    ):
        return "reimporte_liquidado_misma_huella"

    keeper_id = _id_aprobado_menor_misma_cedula(db, row.cedula)
    if keeper_id is not None and int(row.id) != keeper_id:
        n_aprob = int(
            db.scalar(
                select(func.count())
                .select_from(Prestamo)
                .where(
                    Prestamo.estado == "APROBADO",
                    _cedula_norm_expr() == normalizar_cedula_huella(row.cedula),
                )
            )
            or 0
        )
        if n_aprob > 1:
            return "aprobado_extra_ve"

    return None


def listar_aprobados_duplicados_liquidados_sin_pagos(db: Session) -> List[Dict[str, Any]]:
    """
    Candidatos a borrado: solo V/E, sin pagos, re-importe LIQUIDADO o APROBADO extra.
    """
    sin_pagos = not_(
        exists(select(1).select_from(Pago).where(Pago.prestamo_id == Prestamo.id))
    )
    sin_cuota_pagos = not_(
        exists(
            select(1)
            .select_from(CuotaPago)
            .join(Cuota, Cuota.id == CuotaPago.cuota_id)
            .where(Cuota.prestamo_id == Prestamo.id)
        )
    )
    estado_borrable = or_(
        Prestamo.estado == "APROBADO",
        and_(
            Prestamo.estado == ESTADO_PRESTAMO_DESISTIMIENTO,
            Prestamo.observaciones.contains(_NOTA_OBS_DESISTIMIENTO),
        ),
    )
    base = and_(
        _filtro_cedula_ve_sql(),
        sin_pagos,
        sin_cuota_pagos,
        estado_borrable,
    )

    cedula_ap = _cedula_norm_expr()
    ap2 = Prestamo.__table__.alias("ap2")
    cedula_ap2 = func.btrim(func.upper(ap2.c.cedula))
    aprobado_extra = exists(
        select(1)
        .select_from(ap2)
        .where(
            ap2.c.estado == "APROBADO",
            cedula_ap2 == cedula_ap,
            ap2.c.id < Prestamo.id,
        )
    )

    liq = Prestamo.__table__.alias("liq")
    cedula_liq = func.btrim(func.upper(liq.c.cedula))
    reimporte_huella = exists(
        select(1)
        .select_from(liq)
        .where(
            liq.c.estado == "LIQUIDADO",
            cedula_liq == cedula_ap,
            liq.c.fecha_requerimiento == Prestamo.fecha_requerimiento,
            liq.c.total_financiamiento == Prestamo.total_financiamiento,
            liq.c.numero_cuotas == Prestamo.numero_cuotas,
            func.btrim(func.upper(liq.c.modalidad_pago))
            == func.btrim(func.upper(Prestamo.modalidad_pago)),
            func.date(liq.c.fecha_aprobacion) == func.date(Prestamo.fecha_aprobacion),
        )
    )

    rows = list(
        db.execute(
            select(Prestamo).where(base, or_(aprobado_extra, reimporte_huella))
        )
        .scalars()
        .all()
        or []
    )

    out: List[Dict[str, Any]] = []
    for ap in rows:
        motivo = (
            "reimporte_liquidado_misma_huella"
            if existe_liquidado_misma_huella_operativa_prestamo(
                db, ap, exclude_prestamo_id=int(ap.id)
            )
            else "aprobado_extra_ve"
        )
        liq_id = None
        if motivo == "reimporte_liquidado_misma_huella":
            liq_id = db.scalar(
                select(func.min(Prestamo.id)).where(
                    Prestamo.estado == "LIQUIDADO",
                    _cedula_norm_expr() == normalizar_cedula_huella(ap.cedula),
                )
            )
        fa = _fecha_aprobacion_date(ap)
        out.append(
            {
                "cedula": ap.cedula,
                "id_aprobado": int(ap.id),
                "id_liquidado": int(liq_id) if liq_id is not None else None,
                "estado": ap.estado,
                "motivo_borrado": motivo,
                "fecha_aprobacion": fa.isoformat() if fa else None,
                "monto": str(ap.total_financiamiento),
                "numero_cuotas": int(ap.numero_cuotas) if ap.numero_cuotas is not None else None,
                "modalidad": ap.modalidad_pago,
            }
        )
    out.sort(key=lambda x: (str(x.get("cedula") or ""), int(x["id_aprobado"])))
    return out


def corregir_aprobado_duplicado_liquidado(
    db: Session,
    prestamo_id: int,
    *,
    dry_run: bool = True,
) -> Tuple[bool, str]:
    row = db.get(Prestamo, int(prestamo_id))
    if row is None:
        return False, f"prestamo_id={prestamo_id} no encontrado"

    motivo = _motivo_borrado_ve(db, row)
    if not motivo:
        if not cedula_aplica_tope_un_aprobado(row.cedula):
            return False, (
                f"prestamo_id={prestamo_id} cédula tipo J u otra: no aplica borrado automático"
            )
        return False, f"prestamo_id={prestamo_id} no cumple reglas de borrado V/E"

    if dry_run:
        return True, (
            f"[dry-run] borraría prestamo_id={prestamo_id} cedula={row.cedula} "
            f"motivo={motivo}"
        )
    try:
        eliminar_prestamo_por_id(db, int(row.id))
    except IntegrityError as e:
        return False, f"prestamo_id={prestamo_id} no se pudo borrar (restricción BD): {e}"
    except ValueError as e:
        return False, str(e)
    return True, f"borrado prestamo_id={prestamo_id} cedula={row.cedula} motivo={motivo}"


def corregir_todos_aprobados_duplicados_liquidados_sin_pagos(
    db: Session,
    *,
    dry_run: bool = True,
) -> Dict[str, Any]:
    candidatos = listar_aprobados_duplicados_liquidados_sin_pagos(db)
    ok_ids: List[int] = []
    errores: List[Dict[str, Any]] = []
    for item in candidatos:
        pid = int(item["id_aprobado"])
        ok, msg = corregir_aprobado_duplicado_liquidado(db, pid, dry_run=dry_run)
        if ok:
            ok_ids.append(pid)
        else:
            errores.append({"prestamo_id": pid, "error": msg})
    if not dry_run and ok_ids:
        db.commit()
    elif not dry_run:
        db.rollback()
    return {
        "dry_run": dry_run,
        "candidatos": len(candidatos),
        "borrados_ok": len(ok_ids),
        "ids_borrados": ok_ids,
        "errores": errores,
        "detalle_candidatos": candidatos,
    }
