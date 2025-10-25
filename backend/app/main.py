"""
"""
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

# Routers
from app.api.v1.endpoints import (
    amortizacion,
    analistas,
    aprobaciones,
    auditoria,
    auth,
    carga_masiva,
    clientes,
    conciliacion,
    conciliacion_bancaria,
    configuracion,
    dashboard,
    health,
    impact_analysis,
    inteligencia_artificial,
    kpis,
    migracion_emergencia,
    notificaciones,
    notificaciones_multicanal,
    reportes,
    scheduler_notificaciones,
    solicitudes,
    users,
    validadores,
)
from app.core.config import settings
from app.db.init_db import init_db_shutdown, init_db_startup

# Rate Limiting

# Configurar logging básico pero efectivo
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    handlers=[
        logging.StreamHandler(sys.stdout),  # Asegurar que vaya a stdout
    ],
    force=True,  # Forzar reconfiguración
)

logger = logging.getLogger(__name__)

app_logger = logging.getLogger("app")
app_logger.setLevel(getattr(logging, settings.LOG_LEVEL))
app_logger.handlers.clear()
app_logger.addHandler(logging.StreamHandler(sys.stdout))

# Log de inicio
logger.info(
)
logger.info(
    f"Configuración: Environment={settings.ENVIRONMENT}, "
    f"Log Level={settings.LOG_LEVEL}"
)
logger.info(f"CORS Origins: {settings.CORS_ORIGINS}")
logger.info(f"Database URL configurada: {bool(settings.DATABASE_URL)}")

# Configurar rate limiter - TEMPORALMENTE DESACTIVADO
# limiter = Limiter(key_func=get_remote_address)

# ============================================
# SECURITY HEADERS MIDDLEWARE - TEMPORALMENTE PERMISIVO
# ============================================


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware para agregar security headers según OWASP
    - Content-Security-Policy
    - Strict-Transport-Security (HSTS)
    - X-Frame-Options
    - X-Content-Type-Options
    - X-XSS-Protection
    - Referrer-Policy
    """


    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)


        # Permitir iframe para desarrollo
        response.headers["X-Frame-Options"] = "SAMEORIGIN"

        # XSS Protection
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # CSP más permisivo para desarrollo
        response.headers["Content-Security-Policy"] = (
            "default-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob:; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "connect-src 'self' *;"
        )

        # Referrer Policy más permisivo
        response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"

        # Permissions Policy más permisivo
        response.headers["Permissions-Policy"] = (
            "geolocation=*, microphone=*, camera=*"
        )

        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida"""
    init_db_startup()
    yield
    init_db_shutdown()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configurar rate limiter en app state - TEMPORALMENTE DESACTIVADO
# app.state.limiter = limiter
# app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ============================================
# MIDDLEWARES DE SEGURIDAD
# ============================================

# Security Headers - OWASP Best Practices
app.add_middleware(SecurityHeadersMiddleware)

# CORS - MIDDLEWARE SIMPLE PARA OPTIONS
logger.info(
)

# MIDDLEWARE CORS CENTRALIZADO - USANDO CONFIGURACIÓN DE SETTINGS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # Usar configuración de settings
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Accept",
        "Origin",
    ],
)

# Registrar routers
app.include_router(
    health.router, prefix=f"{settings.API_V1_PREFIX}", tags=["Health"]
)
app.include_router(
    auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Auth"]
)
app.include_router(
    users.router,
)
app.include_router(
    clientes.router,
    prefix=f"{settings.API_V1_PREFIX}/clientes",
    tags=["Clientes"],
)
app.include_router(
)
app.include_router(
)
app.include_router(
    conciliacion_bancaria.router,
    prefix=f"{settings.API_V1_PREFIX}/conciliacion-bancaria",
    tags=["Conciliacion Bancaria"],
)
app.include_router(
    amortizacion.router,
    prefix=f"{settings.API_V1_PREFIX}/amortizacion",
    tags=["Amortizacion"],
)
app.include_router(
    conciliacion.router,
    prefix=f"{settings.API_V1_PREFIX}/conciliacion",
    tags=["Conciliacion"],
)
app.include_router(
    reportes.router,
    prefix=f"{settings.API_V1_PREFIX}/reportes",
    tags=["Reportes"],
)
app.include_router(
    kpis.router, prefix=f"{settings.API_V1_PREFIX}/kpis", tags=["KPIs"]
)
app.include_router(
    notificaciones.router,
    prefix=f"{settings.API_V1_PREFIX}/notificaciones",
    tags=["Notificaciones"],
)
app.include_router(
    aprobaciones.router,
    prefix=f"{settings.API_V1_PREFIX}/aprobaciones",
    tags=["Aprobaciones"],
)
app.include_router(
    auditoria.router,
    prefix=f"{settings.API_V1_PREFIX}/auditoria",
    tags=["Auditoria"],
)
app.include_router(
    configuracion.router,
    prefix=f"{settings.API_V1_PREFIX}/configuracion",
    tags=["Configuracion"],
)
app.include_router(
    dashboard.router,
    prefix=f"{settings.API_V1_PREFIX}/dashboard",
    tags=["Dashboard"],
)
app.include_router(
    solicitudes.router,
    prefix=f"{settings.API_V1_PREFIX}/solicitudes",
    tags=["Solicitudes"],
)
app.include_router(
    carga_masiva.router,
    prefix=f"{settings.API_V1_PREFIX}/carga-masiva",
    tags=["Carga Masiva"],
)
app.include_router(
    inteligencia_artificial.router,
    prefix=f"{settings.API_V1_PREFIX}/ia",
    tags=["Inteligencia Artificial"],
)
app.include_router(
    notificaciones_multicanal.router,
    prefix=f"{settings.API_V1_PREFIX}/notificaciones-multicanal",
    tags=["Notificaciones Multicanal"],
)
app.include_router(
    scheduler_notificaciones.router,
    prefix=f"{settings.API_V1_PREFIX}/scheduler",
    tags=["Scheduler"],
)
app.include_router(
    validadores.router,
    prefix=f"{settings.API_V1_PREFIX}/validadores",
    tags=["Validadores"],
)
app.include_router(
)
app.include_router(
    analistas.router,
    prefix=f"{settings.API_V1_PREFIX}/analistas",
    tags=["Analistas"],
)
app.include_router(
)
app.include_router(
    migracion_emergencia.router,
    prefix=f"{settings.API_V1_PREFIX}/migracion",
    tags=["Migración Emergencia"],
)
app.include_router(
    impact_analysis.router,
    prefix=f"{settings.API_V1_PREFIX}/impact",
    tags=["Análisis de Impacto"],
)

# app.include_router(mock_data.router, prefix=f"{settings.API_V1_PREFIX}/mock",


@app.get("/", include_in_schema=False)
async def root():
    return {
        "cors_fixed": True,
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
            "2025-10-25T04:30:00Z"
        ),  # Fix main.py deployment error
        "real_data_ready": True,
    }
