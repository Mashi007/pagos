# backend/app/main.py
"""
Aplicación principal FastAPI - Sistema de Préstamos y Cobranza.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.db.init_db import init_db_startup, init_db_shutdown

# Routers
from app.api.v1.endpoints import (
    health,
    auth,
    users,
    clientes,
    prestamos,
    pagos,
    amortizacion,
    conciliacion,
    reportes,
    kpis,
    notificaciones,
    aprobaciones,
    auditoria,
    configuracion,
    dashboard,
    solicitudes,
    carga_masiva,
    inteligencia_artificial,
    setup_inicial,
    notificaciones_multicanal,
    scheduler_notificaciones,
    validadores,
    diagnostico,
    clientes_temp,
    concesionarios,
    asesores,
)

# Configurar logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida"""
    init_db_startup()
    yield
    init_db_shutdown()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API para gestión de préstamos y cobranza",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers
app.include_router(health.router, prefix=f"{settings.API_V1_PREFIX}", tags=["Health"])
app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Auth"])
app.include_router(users.router, prefix=f"{settings.API_V1_PREFIX}/users", tags=["Users"])
app.include_router(clientes.router, prefix=f"{settings.API_V1_PREFIX}/clientes", tags=["Clientes"])
app.include_router(prestamos.router, prefix=f"{settings.API_V1_PREFIX}/prestamos", tags=["Prestamos"])
app.include_router(pagos.router, prefix=f"{settings.API_V1_PREFIX}/pagos", tags=["Pagos"])
app.include_router(amortizacion.router, prefix=f"{settings.API_V1_PREFIX}/amortizacion", tags=["Amortizacion"])
app.include_router(conciliacion.router, prefix=f"{settings.API_V1_PREFIX}/conciliacion", tags=["Conciliacion"])
app.include_router(reportes.router, prefix=f"{settings.API_V1_PREFIX}/reportes", tags=["Reportes"])
app.include_router(kpis.router, prefix=f"{settings.API_V1_PREFIX}/kpis", tags=["KPIs"])
app.include_router(notificaciones.router, prefix=f"{settings.API_V1_PREFIX}/notificaciones", tags=["Notificaciones"])
app.include_router(aprobaciones.router, prefix=f"{settings.API_V1_PREFIX}/aprobaciones", tags=["Aprobaciones"])
app.include_router(auditoria.router, prefix=f"{settings.API_V1_PREFIX}/auditoria", tags=["Auditoria"])
app.include_router(configuracion.router, prefix=f"{settings.API_V1_PREFIX}/configuracion", tags=["Configuracion"])
app.include_router(dashboard.router, prefix=f"{settings.API_V1_PREFIX}/dashboard", tags=["Dashboard"])
app.include_router(solicitudes.router, prefix=f"{settings.API_V1_PREFIX}/solicitudes", tags=["Solicitudes"])
app.include_router(carga_masiva.router, prefix=f"{settings.API_V1_PREFIX}/carga-masiva", tags=["Carga Masiva"])
app.include_router(inteligencia_artificial.router, prefix=f"{settings.API_V1_PREFIX}/ia", tags=["Inteligencia Artificial"])
app.include_router(setup_inicial.router, prefix=f"{settings.API_V1_PREFIX}/setup", tags=["Setup Inicial"])
app.include_router(notificaciones_multicanal.router, prefix=f"{settings.API_V1_PREFIX}/notificaciones-multicanal", tags=["Notificaciones Multicanal"])
app.include_router(scheduler_notificaciones.router, prefix=f"{settings.API_V1_PREFIX}/scheduler", tags=["Scheduler"])
app.include_router(validadores.router, prefix=f"{settings.API_V1_PREFIX}/validadores", tags=["Validadores"])
app.include_router(diagnostico.router, prefix=f"{settings.API_V1_PREFIX}/diagnostico", tags=["Diagnostico"])
app.include_router(clientes_temp.router, prefix=f"{settings.API_V1_PREFIX}/clientes-temp", tags=["Clientes Temp"])
app.include_router(concesionarios.router, prefix=f"{settings.API_V1_PREFIX}/concesionarios", tags=["Concesionarios"])
app.include_router(asesores.router, prefix=f"{settings.API_V1_PREFIX}/asesores", tags=["Asesores"])


@app.get("/", include_in_schema=False)
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs"
    }
