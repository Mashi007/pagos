"""
Pagos: agregador de routers y reexport de utilidades compartidas.
"""
from app.services.pagos_aplicacion_prestamo import (
    aplicar_pagos_pendientes_prestamo,
    aplicar_pagos_pendientes_prestamo_con_diagnostico,
)
from app.services.pagos_cascada_aplicacion import (
    _aplicar_pago_a_cuotas_interno,
    _marcar_prestamo_liquidado_si_corresponde,
)
from app.services.pagos_cascada_mensajes import _mensaje_sin_aplicacion_cascada

from .cedulas_bs_routes import router as _cedulas_bs_router
from .comprobante_routes import router as _comprobante_router
from .conciliacion_routes import router as _conciliacion_router
from .constants import TZ_NEGOCIO
from .crud_routes import router as _crud_router
from .export_batch_routes import router as _export_batch_router
from .importar_cobros_routes import router as _importar_router
from .kpis_routes import get_pagos_kpis, get_pagos_stats
from .kpis_routes import router as _kpis_router
from .listado_routes import listar_pagos
from .listado_routes import router as _listado_router
from .pago_conciliacion_estado import _estado_conciliacion_post_cascada
from .sql_where_pagos import _where_pago_elegible_reaplicacion_cascada
from .upload_excel_routes import importar_un_pago_reportado_a_pagos
from .upload_excel_routes import router as _upload_router

router = _comprobante_router
for sub in (
    _listado_router,
    _upload_router,
    _importar_router,
    _export_batch_router,
    _conciliacion_router,
    _kpis_router,
    _crud_router,
    _cedulas_bs_router,
):
    router.routes.extend(sub.routes)

__all__ = [
    "TZ_NEGOCIO",
    "_aplicar_pago_a_cuotas_interno",
    "_estado_conciliacion_post_cascada",
    "_marcar_prestamo_liquidado_si_corresponde",
    "_mensaje_sin_aplicacion_cascada",
    "_where_pago_elegible_reaplicacion_cascada",
    "aplicar_pagos_pendientes_prestamo",
    "aplicar_pagos_pendientes_prestamo_con_diagnostico",
    "get_pagos_kpis",
    "get_pagos_stats",
    "importar_un_pago_reportado_a_pagos",
    "listar_pagos",
    "router",
]
