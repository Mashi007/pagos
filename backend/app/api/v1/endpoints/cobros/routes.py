"""
Cobros (admin): agregador de routers y reexport de utilidades internas.
"""
from .escaner_routes import router as _escaner_router
from .listado_kpis_cache import _invalidate_cobros_listado_kpis_cache
from .reportados_helpers import (
    _cedulas_en_clientes_set,
    _list_pagos_reportados_payload,
    actualizar_flag_falla_validadores,
    reportado_falla_validadores_cobros,
)
from .reportados_routes import router as _reportados_router

router = _reportados_router
router.routes.extend(_escaner_router.routes)

__all__ = [
    "_cedulas_en_clientes_set",
    "_invalidate_cobros_listado_kpis_cache",
    "_list_pagos_reportados_payload",
    "actualizar_flag_falla_validadores",
    "reportado_falla_validadores_cobros",
    "router",
]
