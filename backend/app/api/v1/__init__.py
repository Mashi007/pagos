"""
API v1
"""
from fastapi import APIRouter
from app.api.v1.endpoints import whatsapp, auth, configuracion, pagos, notificaciones, dashboard, kpis, auditoria, cobranzas, clientes

api_router = APIRouter()

# Autenticación (login, refresh, me)
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["auth"],
)

# WhatsApp
api_router.include_router(
    whatsapp.router,
    prefix="/whatsapp",
    tags=["whatsapp"],
)

# Configuración general (stub: general, logo)
api_router.include_router(
    configuracion.router,
    prefix="/configuracion",
    tags=["configuracion"],
)

# Pagos (stub: kpis, stats)
api_router.include_router(
    pagos.router,
    prefix="/pagos",
    tags=["pagos"],
)

# Notificaciones (stub: estadisticas/resumen)
api_router.include_router(
    notificaciones.router,
    prefix="/notificaciones",
    tags=["notificaciones"],
)

# Dashboard (stub: opciones-filtros, kpis-principales, admin, etc.)
api_router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["dashboard"],
)

# KPIs (stub: dashboard - usado por DashboardFinanciamiento, DashboardCuotas)
api_router.include_router(
    kpis.router,
    prefix="/kpis",
    tags=["kpis"],
)

# Auditoría (stub: listado, stats, exportar, registrar - hasta tener BD)
api_router.include_router(
    auditoria.router,
    prefix="/auditoria",
    tags=["auditoria"],
)

# Cobranzas (resumen, clientes atrasados, por analista, informes, ML; stub hasta tener BD)
api_router.include_router(
    cobranzas.router,
    prefix="/cobranzas",
    tags=["cobranzas"],
)

# Clientes (listado paginado y stats; stub hasta tener BD)
api_router.include_router(
    clientes.router,
    prefix="/clientes",
    tags=["clientes"],
)
