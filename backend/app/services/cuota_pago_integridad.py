"""
Reglas de integridad entre pagos.monto_pagado y cuota_pagos (suma por pago).

Usado tras aplicar en cascada para detectar sobre-aplicacion (p. ej. 88+96+8 > 96)
y para idempotencia (no re-aplicar si ya existen filas).
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cuota_pago import CuotaPago

# Misma tolerancia que auditoria cartera control 7 / pagos huerfanos
TOLERANCIA_MONTO_PAGO_USD = Decimal("0.02")


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
