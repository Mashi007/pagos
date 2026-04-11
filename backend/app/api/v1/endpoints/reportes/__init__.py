"""
Reportes package - main router that includes all sub-routers.
Prefix: /reportes
"""
from fastapi import APIRouter

from app.api.v1.endpoints.reportes.reportes_dashboard import router as router_dashboard
from app.api.v1.endpoints.reportes.reportes_cliente import router as router_cliente
from app.api.v1.endpoints.reportes.reportes_cartera import router as router_cartera
from app.api.v1.endpoints.reportes.reportes_pagos import router as router_pagos
from app.api.v1.endpoints.reportes.reportes_morosidad import router as router_morosidad
from app.api.v1.endpoints.reportes.reportes_financiero import router as router_financiero
from app.api.v1.endpoints.reportes.reportes_asesores import router as router_asesores
from app.api.v1.endpoints.reportes.reportes_productos import router as router_productos
from app.api.v1.endpoints.reportes.reportes_cedula import router as router_cedula
from app.api.v1.endpoints.reportes.reportes_contable import router as router_contable
from app.api.v1.endpoints.reportes.reportes_conciliacion import router as router_conciliacion
from app.api.v1.endpoints.reportes.reportes_prestamos_fechas import (
    router as router_prestamos_fechas,
)
from app.api.v1.endpoints.reportes.reportes_fecha_drive import (
    router as router_fecha_drive,
)
from app.api.v1.endpoints.reportes.reportes_analisis_financiamiento import (
    router as router_analisis_financiamiento,
)
from app.api.v1.endpoints.reportes.reportes_clientes_hoja import (
    router as router_clientes_hoja,
)
from app.api.v1.endpoints.reportes.reportes_prestamos_drive import (
    router as router_prestamos_drive,
)

router = APIRouter()

router.include_router(router_dashboard, tags=["reportes"])
router.include_router(router_cliente, tags=["reportes"])
router.include_router(router_cartera, tags=["reportes"])
router.include_router(router_pagos, tags=["reportes"])
router.include_router(router_morosidad, tags=["reportes"])
router.include_router(router_financiero, tags=["reportes"])
router.include_router(router_asesores, tags=["reportes"])
router.include_router(router_productos, tags=["reportes"])
router.include_router(router_cedula, tags=["reportes"])
router.include_router(router_contable, tags=["reportes"])
router.include_router(router_conciliacion, tags=["reportes"])
router.include_router(router_prestamos_fechas, tags=["reportes"])
router.include_router(router_fecha_drive, tags=["reportes"])
router.include_router(router_analisis_financiamiento, tags=["reportes"])
router.include_router(router_clientes_hoja, tags=["reportes"])
router.include_router(router_prestamos_drive, tags=["reportes"])

