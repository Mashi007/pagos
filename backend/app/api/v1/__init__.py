"""
API v1
"""
from fastapi import APIRouter
from app.api.v1.endpoints import whatsapp, auth, configuracion, pagos, notificaciones, notificaciones_tabs, dashboard, kpis, auditoria, cobranzas, clientes, tickets, comunicaciones

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

# Notificaciones (estadisticas/resumen, clientes-retrasados, actualizar)
api_router.include_router(
    notificaciones.router,
    prefix="/notificaciones",
    tags=["notificaciones"],
)

# Pestañas de Notificaciones (previas, día pago, retrasadas, prejudicial) - datos reales BD + envío correo por cliente
api_router.include_router(
    notificaciones_tabs.router_previas,
    prefix="/notificaciones-previas",
    tags=["notificaciones-previas"],
)
api_router.include_router(
    notificaciones_tabs.router_dia_pago,
    prefix="/notificaciones-dia-pago",
    tags=["notificaciones-dia-pago"],
)
api_router.include_router(
    notificaciones_tabs.router_retrasadas,
    prefix="/notificaciones-retrasadas",
    tags=["notificaciones-retrasadas"],
)
api_router.include_router(
    notificaciones_tabs.router_prejudicial,
    prefix="/notificaciones-prejudicial",
    tags=["notificaciones-prejudicial"],
)
api_router.include_router(
    notificaciones_tabs.router_mora_61,
    prefix="/notificaciones-mora-61",
    tags=["notificaciones-mora-61"],
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

# Clientes (conectado a BD: listado paginado, stats, CRUD, cambio de estado)
api_router.include_router(
    clientes.router,
    prefix="/clientes",
    tags=["clientes"],
)

# Tickets CRM (conectado a BD clientes + tabla tickets; notificación por correo)
api_router.include_router(
    tickets.router,
    prefix="/tickets",
    tags=["tickets"],
)

# Comunicaciones (WhatsApp/Email). Config en configuracion?tab=whatsapp. Imágenes WhatsApp → pagos_whatsapp.
api_router.include_router(
    comunicaciones.router,
    prefix="/comunicaciones",
    tags=["comunicaciones"],
)
