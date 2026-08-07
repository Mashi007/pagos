"""Reglas de elegibilidad para aplicar cascada sobre un pago."""

from app.models.pago import Pago


def _debe_aplicar_cascada_pago(pago: Pago, user=None) -> bool:
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
    # LIQUIDADO/DESISTIMIENTO: bloquea salvo admin/operador.
    try:
        from app.services.pagos_desistimiento_politica import pago_bloquea_aplicacion_a_cuotas

        if pago_bloquea_aplicacion_a_cuotas(pago, user=user):
            return False
    except Exception:
        pass
    return True