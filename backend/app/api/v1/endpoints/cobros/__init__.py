"""Cobros (admin): router y utilidades internas reutilizadas en tests."""

from .reportados_dedup_helpers import _cedulas_en_clientes_set
from .routes import (
    _invalidate_cobros_listado_kpis_cache,
    _list_pagos_reportados_payload,
    actualizar_flag_falla_validadores,
    reportado_falla_validadores_cobros,
    router,
)

__all__ = [
    "_cedulas_en_clientes_set",
    "_invalidate_cobros_listado_kpis_cache",
    "_list_pagos_reportados_payload",
    "actualizar_flag_falla_validadores",
    "reportado_falla_validadores_cobros",
    "router",
]
