"""

API v1

"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, configuracion, configuracion_informe_pagos, pagos, pagos_gmail, pagos_con_errores, prestamos, prestamos_candidatos_drive, notificaciones, notificaciones_recibos, notificaciones_evidencias, notificaciones_tabs, dashboard, auditoria, clientes, clientes_drive_import, tickets, crm_campanas, comunicaciones, validadores, usuarios, modelos_vehiculos, analistas, concesionarios, ai_training, revision_manual, health, cobros_publico, cobros, cobranzas, estado_cuenta_publico, finiquito, registro_cambios, conciliacion_sheet, admin_tasas_cambio, tasas_cambio_publico, conciliacion_bancos, importacion_extracto

from app.api.v1.endpoints.dashboard import kpis

from app.api.v1.endpoints.reportes import router as reportes_router



api_router = APIRouter()



# Health check (sin autenticaciÃ³n: pÃºblicos para monitoreo)

api_router.include_router(

    health.router,

    tags=["health"],

)



# AutenticaciÃ³n (login, refresh, me)

api_router.include_router(

    auth.router,

    prefix="/auth",

    tags=["auth"],

)


# Logo pÃºblico primero (GET/HEAD sin auth) para que /configuracion/logo/{filename} no requiera token

api_router.include_router(

    configuracion.router_logo,

    prefix="/configuracion",

    tags=["configuracion"],

)

# Callback Google OAuth (pÃºblico; Google redirige aquÃ­ tras autorizar)

api_router.include_router(

    configuracion_informe_pagos.router_google_callback,

    prefix="/configuracion/informe-pagos",

    tags=["configuracion-informe-pagos"],

)

# Cobros: formulario pÃºblico de reporte de pago (sin auth)

api_router.include_router(

    cobros_publico.router,

    prefix="/cobros/public",

    tags=["cobros-public"],

)

# Estado de cuenta pÃºblico: consulta por cÃ©dula, PDF + envÃ­o al email (sin auth)

api_router.include_router(

    estado_cuenta_publico.router,

    prefix="/estado-cuenta/public",

    tags=["estado-cuenta-public"],

)

# Finiquito (portal OTP + admin; materializado jobs lun-sab 01:00 y 13:00 Caracas)

api_router.include_router(

    finiquito.router,

    prefix="/finiquito",

    tags=["finiquito"],

)

# Cobros: administraciÃ³n (con auth)

api_router.include_router(

    cobros.router,

    prefix="/cobros",

    tags=["cobros"],

)

# Cobranzas: gestion de casos, acuerdos e imagenes por prestamo

api_router.include_router(

    cobranzas.router,

    prefix="/cobranzas",

    tags=["cobranzas"],

)

from app.api.v1.endpoints.cobranzas import gestores_routes as cobranzas_gestores

api_router.include_router(
    cobranzas_gestores.router,
    prefix="/cobranzas/gestores",
    tags=["cobranzas-gestores"],
)

# Tasas de cambio (admin): /api/v1/admin/tasas-cambio/*
api_router.include_router(
    admin_tasas_cambio.router,
    tags=["admin-tasas-cambio"],
)

# Tasas de cambio (lectura para autenticados): /api/v1/tasas-cambio/*
api_router.include_router(
    tasas_cambio_publico.router,
    tags=["tasas-cambio"],
)

# ConfiguraciÃ³n general (general, upload-logo, delete logo; con auth)

api_router.include_router(

    configuracion.router,

    prefix="/configuracion",

    tags=["configuracion"],

)



# Pagos con errores (Revisar Pagos) DEBE ir antes que /pagos para que GET /pagos/con-errores no coincida con GET /pagos/{pago_id} (evitar 422)

api_router.include_router(

    pagos_con_errores.router,

    prefix="/pagos/con-errores",

    tags=["pagos-con-errores"],

)

# Pagos (datos reales BD: kpis, stats)

api_router.include_router(

    pagos.router,

    prefix="/pagos",

    tags=["pagos"],

)



# Pagos Gmail (pipeline Gmail -> Drive -> Gemini -> Sheets)

api_router.include_router(

    pagos_gmail.router,

    prefix="/pagos/gmail",

    tags=["pagos-gmail"],

)

# Hoja CONCILIACIÃ“N (Google Sheets) â†’ snapshot en BD (cron con secreto)

api_router.include_router(

    conciliacion_sheet.router,

    prefix="/conciliacion-sheet",

    tags=["conciliacion-sheet"],

)

# PrÃ©stamos (datos reales BD: listado, stats, CRUD)

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

api_router.include_router(
    notificaciones_recibos.router,
    prefix="/notificaciones/recibos",
    tags=["notificaciones-recibos"],
)

api_router.include_router(
    notificaciones_evidencias.router,
    prefix="/notificaciones/evidencias",
    tags=["notificaciones-evidencias"],
)



# PestaÃ±as de Notificaciones (previas, dÃ­a pago, retrasadas, prejudicial) - datos reales BD + envÃ­o correo por cliente

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
    notificaciones_tabs.router_estado_cuenta,
    prefix="/notificaciones-estado-cuenta",
    tags=["notificaciones-estado-cuenta"],
)

api_router.include_router(
    notificaciones_tabs.router_cobranzas,
    prefix="/notificaciones-cobranzas",
    tags=["notificaciones-cobranzas"],
)

api_router.include_router(
    notificaciones_tabs.router_cuotas_4_mas,
    prefix="/notificaciones-cuotas-4-mas",
    tags=["notificaciones-cuotas-4-mas"],
)


api_router.include_router(

    notificaciones_tabs.router_masivos,

    prefix="/notificaciones-masivos",

    tags=["notificaciones-masivos"],

)

# Dashboard (KPIs, graficos, filtros; datos reales BD + caches programadas en dashboard/__init__.py)

api_router.include_router(

    dashboard.router,

    prefix="/dashboard",

    tags=["dashboard"],

)



# KPIs (prefijo /kpis: mismos datos BD que dashboard; usado por DashboardFinanciamiento, DashboardCuotas)

api_router.include_router(

    kpis.router,

    prefix="/kpis",

    tags=["kpis"],

)



# Auditoria (listado, stats, exportar, registrar; datos reales BD)

api_router.include_router(

    auditoria.router,

    prefix="/auditoria",

    tags=["auditoria"],

)

# Conciliacion Bancos (Auditoria): Excel banco vs numero_documento OCR

api_router.include_router(

    conciliacion_bancos.router,

    tags=["conciliacion-bancos"],

)

# Importacion extracto faltantes (Auditoria): Excel banco → altas autorizadas

api_router.include_router(

    importacion_extracto.router,

    tags=["importacion-extracto"],

)

# Registro de Cambios (historial de cambios con usuario, fecha, descripciÃ³n)

api_router.include_router(

    registro_cambios.router,

    tags=["auditoria"],

)



# Reportes (dashboard/resumen con datos reales BD)

api_router.include_router(

    reportes_router,

    prefix="/reportes",

    tags=["reportes"],

)



# Clientes (conectado a BD: listado paginado, stats, CRUD, cambio de estado)

api_router.include_router(

    clientes.router,

    prefix="/clientes",

    tags=["clientes"],

)

api_router.include_router(
    clientes_drive_import.router,
    prefix="/clientes/drive-import",
    tags=["clientes"],
)

api_router.include_router(
    prestamos_candidatos_drive.router,
    prefix="/prestamos/candidatos-drive",
    tags=["prestamos"],
)


# Tickets CRM (conectado a BD clientes + tabla tickets; notificaciÃ³n por correo)

api_router.include_router(

    tickets.router,

    prefix="/tickets",

    tags=["tickets"],

)




# CRM CampaÃ±as (envÃ­o por lotes a correos de tabla clientes)
api_router.include_router(
    crm_campanas.router,
    prefix="/crm/campanas",
    tags=["crm-campanas"],
)
# Comunicaciones (WhatsApp/Email). Config en configuracion?tab=whatsapp. Comprobante WhatsApp â†’ pago_comprobante_imagen (FK pagos_whatsapp).

api_router.include_router(

    comunicaciones.router,

    prefix="/comunicaciones",

    tags=["comunicaciones"],

)



# Validadores (cÃ©dula, telÃ©fono, email, fecha). ConfiguraciÃ³n > Validadores.

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



# Modelos de vehÃ­culos (solo lectura desde distinct Prestamo.modelo_vehiculo; CRUD 501).

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



# AI Training (mÃ©tricas de conversaciones, fine-tuning, RAG, ML riesgo).

api_router.include_router(

    ai_training.router,

    prefix="/ai/training",

    tags=["ai-training"],

)



# RevisiÃ³n Manual de PrÃ©stamos (post-migraciÃ³n: monitoreo y verificaciÃ³n manual)

api_router.include_router(

    revision_manual.router,

    prefix="/revision-manual",

    tags=["revision-manual"],

)








