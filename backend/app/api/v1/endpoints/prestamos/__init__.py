"""Préstamos: router FastAPI y símbolos reutilizados por otros módulos."""

from .routes import (
    _generar_cuotas_amortizacion,
    _listado_cuotas_prestamo_dicts,
    _recalcular_fechas_vencimiento_cuotas,
    _reconstruir_tabla_cuotas_desde_prestamo_en_sesion,
    _resolver_monto_cuota,
    crear_prestamo_servicio_interno,
    listar_prestamos,
    router,
    update_prestamo,
)

__all__ = [
    "_generar_cuotas_amortizacion",
    "_listado_cuotas_prestamo_dicts",
    "_recalcular_fechas_vencimiento_cuotas",
    "_reconstruir_tabla_cuotas_desde_prestamo_en_sesion",
    "_resolver_monto_cuota",
    "crear_prestamo_servicio_interno",
    "listar_prestamos",
    "router",
    "update_prestamo",
]
