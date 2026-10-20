"""
Reglas de integridad entre pagos.monto_pagado y cuota_pagos (suma por pago).

Usado tras aplicar en cascada para detectar sobre-aplicacion (p. ej. 88+96+8 > 96)
y para idempotencia (no re-aplicar si ya existen filas).

Tambien: evitar regenerar limbo (PAGADO/conciliado sin cuota_pagos cuando aun hay cupo
en cuotas). Portal Infopagos y Gmail ABCD ya fallan/revierten; Excel y Cobros staff
deben usar ``pago_quedaria_limbo_pagado_sin_cuotas`` / ``demotar_pago_sin_aplicacion``.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.cuota_pago import CuotaPago

# Misma tolerancia que auditoria cartera control 7 / pagos huerfanos
TOLERANCIA_MONTO_PAGO_USD = Decimal("0.02")
# Cupo minimo en cuotas para considerar que "debio" articulase (alineado export_batch)
_TOL_CUPO_APLICABLE_USD = Decimal("0.01")


def suma_monto_aplicado_pago(db: Session, pago_id: int) -> Decimal:
    r = db.scalar(
        select(func.coalesce(func.sum(CuotaPago.monto_aplicado), 0)).where(
            CuotaPago.pago_id == pago_id
        )
    )
    return Decimal(str(r or 0))


def pago_tiene_aplicaciones_cuotas(db: Session, pago_id: int) -> bool:
    n = (
        db.scalar(
            select(func.count()).select_from(CuotaPago).where(
                CuotaPago.pago_id == pago_id
            )
        )
        or 0
    )
    return int(n) > 0


def prestamo_tiene_cupo_aplicable_en_cuotas(
    db: Session, prestamo_id: Optional[int]
) -> bool:
    """
    True si el prestamo tiene al menos una cuota operativa con saldo > tol.

    Mismo criterio practico que export_batch (cuotas PENDIENTE/VENCIDO/MORA/PARCIAL
    con monto - aplicado_en_cuota_pagos > 0.01). Usa total_pagado de la cuota como
    proxy rapido (coherente con amortizacion UI).
    """
    if prestamo_id is None:
        return False
    try:
        pid = int(prestamo_id)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False

    from app.models.cuota import Cuota

    saldo = func.coalesce(Cuota.monto, 0) - func.coalesce(Cuota.total_pagado, 0)
    q = (
        select(1)
        .select_from(Cuota)
        .where(
            and_(
                Cuota.prestamo_id == pid,
                Cuota.estado.in_(("PENDIENTE", "VENCIDO", "MORA", "PARCIAL")),
                saldo > float(_TOL_CUPO_APLICABLE_USD),
            )
        )
        .limit(1)
    )
    return db.execute(q).first() is not None


def demotar_pago_sin_aplicacion(pago: Any) -> None:
    """Baja a PENDIENTE y quita marcas de conciliacion (evita limbo operativo)."""
    pago.estado = "PENDIENTE"
    pago.conciliado = False
    pago.fecha_conciliacion = None
    ver = str(getattr(pago, "verificado_concordancia", None) or "").strip().upper()
    if ver == "SI":
        pago.verificado_concordancia = "NO"


def pago_quedaria_limbo_pagado_sin_cuotas(db: Session, pago: Any) -> bool:
    """
    True si dejar el pago como PAGADO/conciliado regeneraria control-15 «mal»:
    sin filas en cuota_pagos y aun hay cupo en cuotas del prestamo.

    Excepciones (False): ABONOS / Conciliar cartera (preservan autoconciliacion sin
    cuotas), sin prestamo_id, o ya tiene aplicaciones.
    """
    pago_id = getattr(pago, "id", None)
    if pago_id is None:
        return False
    if pago_tiene_aplicaciones_cuotas(db, int(pago_id)):
        return False

    from app.services.pago_autoconciliacion import pago_preserva_autoconciliacion_sin_cuotas

    if pago_preserva_autoconciliacion_sin_cuotas(pago):
        return False

    prestamo_id = getattr(pago, "prestamo_id", None)
    return prestamo_tiene_cupo_aplicable_en_cuotas(db, prestamo_id)


def validar_suma_aplicada_vs_monto_pago(
    db: Session, pago_id: int, monto_pagado
) -> None:
    """
    Raises ValueError si SUM(cuota_pagos.monto_aplicado) > monto_pagado + tolerancia.
    Llamar despues de db.flush() para incluir filas nuevas en la sesion.
    """
    mp = Decimal(str(monto_pagado or 0))
    s = suma_monto_aplicado_pago(db, pago_id)
    if s > mp + TOLERANCIA_MONTO_PAGO_USD:
        raise ValueError(
            f"Suma aplicada a cuotas ({s}) supera monto del pago ({mp}) "
            f"para pago_id={pago_id}. Revise cuota_pagos o use reaplicacion en cascada."
        )
