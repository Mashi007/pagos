"""
API v1
"""
from fastapi import APIRouter
from app.api.v1.endpoints import whatsapp, auth, configuracion, pagos, notificaciones, dashboard, kpis

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
