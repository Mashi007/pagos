"""
Cobros (admin): agregador de routers y reexport de utilidades internas.
"""
from .escaner_routes import router as _escaner_router
from .listado_kpis_cache import _invalidate_cobros_listado_kpis_cache
from .reportados_dedup_helpers import _cedulas_en_clientes_set
from .reportados_listado_payload import _list_pagos_reportados_payload
from .reportados_routes import router as _reportados_router
from .reportados_validadores_helpers import (
    actualizar_flag_falla_validadores,
    reportado_falla_validadores_cobros,
)

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
