"""
Estado del préstamo alineado con cuotas en respuestas API.

Si en BD sigue APROBADO pero todas las cuotas tienen cobertura completa (misma
tolerancia que _marcar_prestamo_liquidado_si_corresponde en pagos, que tambien
puede pasar LIQUIDADO a APROBADO si queda saldo en cuotas), la lista y el detalle
pueden exponer estado coherente con cuotas.
"""
from __future__ import annotations

from typing import Any, Optional, Set

from sqlalchemy import and_, case, exists, func, not_, or_, select
from sqlalchemy.orm import Session

from app.models.cuota import Cuota
from app.models.prestamo import Prestamo

_TOL = 0.01


def prestamo_bloquea_insertar_filas_cuota_si_liquidado_bd(p: Prestamo) -> Optional[str]:
    """
    None si se pueden insertar filas en la tabla cuotas.
    Solo estado LIQUIDADO en BD (no usar liquidacion efectiva aqui: en la misma transaccion
    puede haberse hecho DELETE de cuotas antes de regenerar, p. ej. aprobacion manual).
    """
    if (p.estado or "").strip().upper() == "LIQUIDADO":
        return (
            "El préstamo está liquidado; no se pueden agregar ni regenerar cuotas."
        )
    return None


def prestamo_bloquea_nuevas_cuotas_o_cambio_plazo(db: Session, p: Prestamo) -> Optional[str]:
    """
    None si se permiten cambiar numero_cuotas o generar la primera tabla de amortizacion.
    Incluye liquidacion en BD y liquidacion efectiva (APROBADO con todas las cuotas cubiertas).
    """
    msg_bd = prestamo_bloquea_insertar_filas_cuota_si_liquidado_bd(p)
    if msg_bd:
        return (
            "El préstamo está liquidado; no se pueden agregar cuotas ni modificar el número de cuotas."
        )
    if p.id in prestamo_ids_aprobados_todas_cuotas_cubiertas(db, [p.id]):
        return (
            "El préstamo está liquidado (todas las cuotas cubiertas); no se pueden agregar cuotas "
            "ni modificar el número de cuotas."
        )
    return None


def prestamo_ids_aprobados_todas_cuotas_cubiertas(
    db: Session, prestamo_ids: list[int]
) -> Set[int]:
    """
    Subconjunto de prestamo_ids: estado APROBADO, al menos una cuota, ninguna con saldo pendiente.
    """
    if not prestamo_ids:
        return set()
    aprobados = (
        db.execute(
            select(Prestamo.id).where(
                Prestamo.id.in_(prestamo_ids),
                Prestamo.estado == "APROBADO",
            )
        )
        .scalars()
        .all()
    )
    if not aprobados:
        return set()

    pendientes = func.sum(
        case(
            (
                or_(
                    Cuota.total_pagado.is_(None),
                    Cuota.total_pagado < (Cuota.monto - _TOL),
                ),
                1,
            ),
            else_=0,
        )
    )
    n_cuotas = func.count()

    rows = db.execute(
        select(Cuota.prestamo_id, n_cuotas, pendientes)
        .where(Cuota.prestamo_id.in_(aprobados))
        .group_by(Cuota.prestamo_id)
    ).all()

    out: Set[int] = set()
    for pid, n, pend in rows:
        if not n or int(n) <= 0:
            continue
        pnum = float(pend) if pend is not None else 0.0
        if pnum < 0.5:
            out.add(int(pid))
    return out


def condicion_filtro_estado_prestamo(est: str) -> Optional[Any]:
    """
    Condición SQLAlchemy para filtrar por estado coherente con cuotas.

    - LIQUIDADO: fila en BD LIQUIDADO o APROBADO con al menos una cuota y todas cubiertas.
    - APROBADO: APROBADO en BD y (sin cuotas o alguna cuota aún con saldo).
    - Otros códigos: None (usar Prestamo.estado == est).
    """
    est = (est or "").strip().upper()
    if est not in ("APROBADO", "LIQUIDADO"):
        return None

    cuota_incompleta = exists(
        select(1).where(
            Cuota.prestamo_id == Prestamo.id,
            or_(
                Cuota.total_pagado.is_(None),
                Cuota.total_pagado < (Cuota.monto - _TOL),
            ),
        )
    )
    tiene_cuotas = exists(select(1).where(Cuota.prestamo_id == Prestamo.id))

    aprobado_liquidado_efectivo = and_(
        Prestamo.estado == "APROBADO",
        tiene_cuotas,
        not_(cuota_incompleta),
    )

    if est == "LIQUIDADO":
        return or_(Prestamo.estado == "LIQUIDADO", aprobado_liquidado_efectivo)

    # APROBADO
    return and_(Prestamo.estado == "APROBADO", or_(not_(tiene_cuotas), cuota_incompleta))
