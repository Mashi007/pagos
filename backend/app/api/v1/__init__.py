"""
API v1
"""
from fastapi import APIRouter
from app.api.v1.endpoints import whatsapp, auth, configuracion, configuracion_informe_pagos, pagos, prestamos, notificaciones, notificaciones_tabs, dashboard, kpis, auditoria, cobranzas, clientes, tickets, comunicaciones, validadores, usuarios, reportes, modelos_vehiculos, analistas, concesionarios, ai_training

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

# Logo público primero (GET/HEAD sin auth) para que /configuracion/logo/{filename} no requiera token
api_router.include_router(
    configuracion.router_logo,
    prefix="/configuracion",
    tags=["configuracion"],
)
# Callback Google OAuth (público; Google redirige aquí tras autorizar)
api_router.include_router(
    configuracion_informe_pagos.router_google_callback,
    prefix="/configuracion/informe-pagos",
    tags=["configuracion-informe-pagos"],
)
# Configuración general (general, upload-logo, delete logo; con auth)
api_router.include_router(
    configuracion.router,
    prefix="/configuracion",
    tags=["configuracion"],
)

# Pagos (datos reales BD: kpis, stats)
api_router.include_router(
    pagos.router,
    prefix="/pagos",
    tags=["pagos"],
)

# Préstamos (datos reales BD: listado, stats, CRUD)
api_router.include_router(
    prestamos.router,
    prefix="/prestamos",
    tags=["prestamos"],
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

# Reportes (dashboard/resumen con datos reales BD)
api_router.include_router(
    reportes.router,
    prefix="/reportes",
    tags=["reportes"],
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

# Validadores (cédula, teléfono, email, fecha). Configuración > Validadores.
api_router.include_router(
    validadores.router,
    prefix="/validadores",
    tags=["validadores"],
)

# Usuarios (sin tabla users: listado desde ADMIN_EMAIL para Tickets/Comunicaciones).
api_router.include_router(
    usuarios.router,
    prefix="/usuarios",
    tags=["usuarios"],
)

# Modelos de vehículos (solo lectura desde distinct Prestamo.modelo_vehiculo; CRUD 501).
api_router.include_router(
    modelos_vehiculos.router,
    prefix="/modelos-vehiculos",
    tags=["modelos-vehiculos"],
)

# Concesionarios (solo lectura desde distinct Prestamo.concesionario; GET /activos para dropdowns).
api_router.include_router(
    concesionarios.router,
    prefix="/concesionarios",
    tags=["concesionarios"],
)

# Analistas (solo lectura desde distinct Prestamo.analista; GET /activos para dropdowns).
api_router.include_router(
    analistas.router,
    prefix="/analistas",
    tags=["analistas"],
)

# AI Training (métricas de conversaciones, fine-tuning, RAG, ML riesgo).
api_router.include_router(
    ai_training.router,
    prefix="/ai/training",
    tags=["ai-training"],
)
