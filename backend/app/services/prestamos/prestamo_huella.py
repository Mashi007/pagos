"""
Huella estricta de prestamo (alineada a scripts/sql/plan_duplicados_prestamos.sql):
misma cedula normalizada, fecha_requerimiento, montos y plazos que agrupan duplicados en SQL.

Solo bloquea un segundo APROBADO con la misma huella (no compara contra LIQUIDADO/RECHAZADO).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.prestamo import Prestamo

_TOL_CUOTA = Decimal("0.01")


def normalizar_cedula_huella(cedula: str | None) -> str:
    return (cedula or "").strip().upper()


def normalizar_modalidad_producto(valor: str | None) -> str:
    return (valor or "").strip().upper()


def _decimal_o_cero(v: Decimal | None) -> Decimal:
    return v if v is not None else Decimal("0")


def contar_otros_aprobados_misma_huella(
    db: Session,
    *,
    cedula: str | None,
    fecha_requerimiento: date | None,
    total_financiamiento: Decimal | None,
    numero_cuotas: int | None,
    cuota_periodo: Decimal | None,
    tasa_interes: Decimal | None,
    modalidad_pago: str | None,
    producto: str | None,
    exclude_prestamo_id: int | None = None,
) -> int:
    """
    Cuenta prestamos en estado APROBADO con la misma huella que plan_duplicados (GROUP BY estricto).
    """
    if fecha_requerimiento is None:
        return 0

    cedula_n = normalizar_cedula_huella(cedula)
    modalidad_n = normalizar_modalidad_producto(modalidad_pago)
    producto_n = normalizar_modalidad_producto(producto)
    tasa_cmp = _decimal_o_cero(tasa_interes)
    cuota_per_cmp = _decimal_o_cero(cuota_periodo)

    cond = [
        Prestamo.estado == "APROBADO",
        func.btrim(func.upper(Prestamo.cedula)) == cedula_n,
        Prestamo.fecha_requerimiento == fecha_requerimiento,
        Prestamo.total_financiamiento == total_financiamiento,
        Prestamo.numero_cuotas == numero_cuotas,
        Prestamo.cuota_periodo == cuota_per_cmp,
        Prestamo.tasa_interes == tasa_cmp,
        func.btrim(func.upper(Prestamo.modalidad_pago)) == modalidad_n,
        func.btrim(func.upper(Prestamo.producto)) == producto_n,
    ]
    if exclude_prestamo_id is not None:
        cond.append(Prestamo.id != exclude_prestamo_id)

    q = select(func.count()).select_from(Prestamo).where(*cond)
    return int(db.scalar(q) or 0)


def ensure_no_duplicate_aprobado_huella(
    db: Session,
    prestamo: Prestamo,
    *,
    exclude_prestamo_id: int | None = None,
) -> None:
    """HTTP 409 si ya existe otro APROBADO con la misma huella."""
    if (prestamo.estado or "").upper() != "APROBADO":
        return

    excl: int | None = exclude_prestamo_id
    if excl is None and getattr(prestamo, "id", None) is not None:
        excl = int(prestamo.id)

    n = contar_otros_aprobados_misma_huella(
        db,
        cedula=prestamo.cedula,
        fecha_requerimiento=prestamo.fecha_requerimiento,
        total_financiamiento=prestamo.total_financiamiento,
        numero_cuotas=prestamo.numero_cuotas,
        cuota_periodo=prestamo.cuota_periodo,
        tasa_interes=_decimal_o_cero(getattr(prestamo, "tasa_interes", None)),
        modalidad_pago=prestamo.modalidad_pago,
        producto=prestamo.producto,
        exclude_prestamo_id=excl,
    )
    if n > 0:
        raise HTTPException(
            status_code=409,
            detail=(
                "Ya existe otro prestamo APROBADO con la misma huella (cedula, fecha requerimiento, "
                "monto, cuotas, modalidad y producto). Revise duplicados antes de continuar."
            ),
        )


def count_prestamos_al_dia(db: Session) -> int:
    """
    Prestamos APROBADO donde toda cuota con vencimiento <= hoy (America/Caracas) esta cubierta al 100%.
    Misma regla que scripts/sql/vista_prestamos_al_dia.sql (tolerancia 0.01 en montos).
    """
    sql = text(
        """
        SELECT COUNT(*)::bigint
        FROM prestamos p
        WHERE p.estado = 'APROBADO'
          AND NOT EXISTS (
            SELECT 1
            FROM cuotas c
            WHERE c.prestamo_id = p.id
              AND c.fecha_vencimiento <= (timezone('America/Caracas', now()))::date
              AND COALESCE(c.total_pagado, 0) < COALESCE(c.monto_cuota, 0) - :tol
          )
        """
    )
    row = db.execute(sql, {"tol": _TOL_CUOTA}).scalar()
    return int(row or 0)
