"""Reglas de elegibilidad para aplicar cascada sobre un pago."""

from app.models.pago import Pago


def _debe_aplicar_cascada_pago(pago: Pago) -> bool:
    """Regla unica de seguridad para aplicar pagos en cascada."""
    if not pago.prestamo_id:
        return False
    if float(pago.monto_pagado or 0) <= 0:
        return False
    if not bool(getattr(pago, "conciliado", False)):
        return False
    estado = str(getattr(pago, "estado", "") or "").upper()
    if estado in ("DUPLICADO", "ANULADO_IMPORT"):
        return False
    return True
