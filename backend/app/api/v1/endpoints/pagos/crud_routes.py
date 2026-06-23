"""Pagos CRUD: agregador de sub-routers."""
from .crud_batch_routes import router as _batch_router
from .crud_pagos_aplicacion_routes import router as _aplicacion_router
from .crud_pagos_mutation_routes import router as _mutation_router

router = _batch_router
router.routes.extend(_mutation_router.routes)
router.routes.extend(_aplicacion_router.routes)
