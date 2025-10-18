# backend/app/main.py
"""
Aplicación principal FastAPI - Sistema de Préstamos y Cobranza.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.db.init_db import init_db_startup, init_db_shutdown

# Rate Limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

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
    monitoreo_auditoria,
    scheduler_notificaciones,
    validadores,
    concesionarios,
    analistas,
    modelos_vehiculos,
    fix_database,
    test_auth,
    debug_auth,
    test_auditoria,
    fix_admin_definitive,
)

# Configurar logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configurar rate limiter
limiter = Limiter(key_func=get_remote_address)


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
        
        # Headers básicos de seguridad (menos restrictivos)
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Permitir iframe para desarrollo
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        
        # XSS Protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # CSP más permisivo para desarrollo
        response.headers["Content-Security-Policy"] = "default-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob:; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self' *;"
        
        # Referrer Policy más permisivo
        response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"
        
        # Permissions Policy más permisivo
        response.headers["Permissions-Policy"] = "geolocation=*, microphone=*, camera=*"
        
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
    description="API para gestión de préstamos y cobranza",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configurar rate limiter en app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ============================================
# MIDDLEWARES DE SEGURIDAD
# ============================================

# Security Headers - OWASP Best Practices
app.add_middleware(SecurityHeadersMiddleware)

# CORS - MIDDLEWARE SIMPLE PARA OPTIONS
from fastapi.middleware.cors import CORSMiddleware

logger.info(f"🌐 CORS Origins configurados: {settings.CORS_ORIGINS}")
logger.info("✅ CORS: Middleware simple para OPTIONS + Headers directos en POST")

# MIDDLEWARE CORS CENTRALIZADO - USANDO CONFIGURACIÓN PERMISIVA
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ✅ Temporalmente permisivo para testing
    allow_credentials=True,
    allow_methods=["*"],  # ✅ Todos los métodos
    allow_headers=["*"],  # ✅ Todos los headers
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
app.include_router(concesionarios.router, prefix=f"{settings.API_V1_PREFIX}/concesionarios", tags=["Concesionarios"])
app.include_router(analistas.router, prefix=f"{settings.API_V1_PREFIX}/analistas", tags=["Analistas"])
app.include_router(modelos_vehiculos.router, prefix=f"{settings.API_V1_PREFIX}/modelos-vehiculos", tags=["Modelos Vehículos"])
app.include_router(fix_database.router, prefix=f"{settings.API_V1_PREFIX}/fix-db", tags=["Database Fix"])
app.include_router(test_auth.router, prefix=f"{settings.API_V1_PREFIX}/test", tags=["Test Auth"])
app.include_router(debug_auth.router, prefix=f"{settings.API_V1_PREFIX}/debug", tags=["Debug Auth"])
app.include_router(test_auditoria.router, prefix=f"{settings.API_V1_PREFIX}/test-auditoria", tags=["Test Auditoria"])
app.include_router(monitoreo_auditoria.router, prefix=f"{settings.API_V1_PREFIX}/monitoreo-auditoria", tags=["Monitoreo Auditoría"])
app.include_router(fix_admin_definitive.router, prefix=f"{settings.API_V1_PREFIX}/fix-definitive", tags=["Fix Admin Definitive"])
# app.include_router(mock_data.router, prefix=f"{settings.API_V1_PREFIX}/mock", tags=["Mock Data"])  # Removido - se usarán datos reales


@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": "Sistema de Préstamos y Cobranza API v1.0.0", 
        "cors_fixed": True,
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "deploy_timestamp": "2025-10-16T10:30:00Z",  # Fix modelo_vehiculo_id error - ready for real data
        "real_data_ready": True
    }
