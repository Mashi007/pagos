"""Compat: la lógica vive en app.services.cuota_transiciones_pago."""

from app.services.cuota_transiciones_pago import validar_transicion_estado_cuota as _validar_transicion_estado_cuota

__all__ = ["_validar_transicion_estado_cuota"]
