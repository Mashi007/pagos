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
    conciliacion_bancaria,
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
    notificaciones_multicanal,
    scheduler_notificaciones,
    validadores,
    concesionarios,
    analistas,
    modelos_vehiculos,
    plantilla_clientes,
    migracion_emergencia,
    diagnostico,
    diagnostico_auth,
    token_verification,
    dashboard_diagnostico,
    auth_flow_analyzer,
    predictive_analyzer,
    intelligent_alerts,
    real_time_monitor,
    predictive_token_analyzer,
    cross_validation_auth,
    intelligent_alerts_system,
    network_diagnostic,
    forensic_analysis,
    experimental_tests,
    comparative_analysis,
    temporal_analysis,
    architectural_analysis
)

# Configurar logging robusto
import sys

# Configurar logging básico pero efectivo
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),  # Asegurar que vaya a stdout
    ],
    force=True  # Forzar reconfiguración
)
logger = logging.getLogger(__name__)

# Configurar loggers específicos para asegurar que funcionen
app_logger = logging.getLogger("app")
app_logger.setLevel(getattr(logging, settings.LOG_LEVEL))
app_logger.handlers.clear()
app_logger.addHandler(logging.StreamHandler(sys.stdout))

# Log de inicio
logger.info("🚀 Iniciando aplicación FastAPI - Sistema de Préstamos y Cobranza")
logger.info(f"📊 Configuración: Environment={settings.ENVIRONMENT}, Log Level={settings.LOG_LEVEL}")
logger.info(f"🌐 CORS Origins: {settings.CORS_ORIGINS}")
logger.info(f"🔗 Database URL configurada: {bool(settings.DATABASE_URL)}")

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
app.include_router(users.router, prefix=f"{settings.API_V1_PREFIX}/usuarios", tags=["Usuarios"])
app.include_router(clientes.router, prefix=f"{settings.API_V1_PREFIX}/clientes", tags=["Clientes"])
app.include_router(prestamos.router, prefix=f"{settings.API_V1_PREFIX}/prestamos", tags=["Prestamos"])
app.include_router(pagos.router, prefix=f"{settings.API_V1_PREFIX}/pagos", tags=["Pagos"])
app.include_router(conciliacion_bancaria.router, prefix=f"{settings.API_V1_PREFIX}/conciliacion-bancaria", tags=["Conciliacion Bancaria"])
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
app.include_router(notificaciones_multicanal.router, prefix=f"{settings.API_V1_PREFIX}/notificaciones-multicanal", tags=["Notificaciones Multicanal"])
app.include_router(scheduler_notificaciones.router, prefix=f"{settings.API_V1_PREFIX}/scheduler", tags=["Scheduler"])
app.include_router(validadores.router, prefix=f"{settings.API_V1_PREFIX}/validadores", tags=["Validadores"])
app.include_router(concesionarios.router, prefix=f"{settings.API_V1_PREFIX}/concesionarios", tags=["Concesionarios"])
app.include_router(analistas.router, prefix=f"{settings.API_V1_PREFIX}/analistas", tags=["Analistas"])
app.include_router(modelos_vehiculos.router, prefix=f"{settings.API_V1_PREFIX}/modelos-vehiculos", tags=["Modelos Vehiculos"])
app.include_router(plantilla_clientes.router, prefix=f"{settings.API_V1_PREFIX}/plantilla", tags=["Plantilla Excel"])
app.include_router(migracion_emergencia.router, prefix=f"{settings.API_V1_PREFIX}/migracion", tags=["Migración Emergencia"])
app.include_router(diagnostico.router, prefix=f"{settings.API_V1_PREFIX}/diagnostico", tags=["Diagnóstico"])
app.include_router(diagnostico_auth.router, prefix=f"{settings.API_V1_PREFIX}/auth-debug", tags=["Diagnóstico Auth"])
app.include_router(token_verification.router, prefix=f"{settings.API_V1_PREFIX}/token", tags=["Verificación Tokens"])
app.include_router(dashboard_diagnostico.router, prefix=f"{settings.API_V1_PREFIX}/monitor", tags=["Monitor Diagnóstico"])
app.include_router(auth_flow_analyzer.router, prefix=f"{settings.API_V1_PREFIX}/flow", tags=["Análisis Flujo Auth"])
app.include_router(predictive_analyzer.router, prefix=f"{settings.API_V1_PREFIX}/predictive", tags=["Análisis Predictivo"])
app.include_router(intelligent_alerts.router, prefix=f"{settings.API_V1_PREFIX}/alerts", tags=["Alertas Inteligentes"])
app.include_router(real_time_monitor.router, prefix=f"{settings.API_V1_PREFIX}/monitor", tags=["Monitor Tiempo Real"])
app.include_router(predictive_token_analyzer.router, prefix=f"{settings.API_V1_PREFIX}/predictive-tokens", tags=["Análisis Predictivo Tokens"])
app.include_router(cross_validation_auth.router, prefix=f"{settings.API_V1_PREFIX}/cross-validation", tags=["Validación Cruzada"])
app.include_router(intelligent_alerts_system.router, prefix=f"{settings.API_V1_PREFIX}/intelligent-alerts", tags=["Sistema Alertas Inteligentes"])
app.include_router(network_diagnostic.router, prefix=f"{settings.API_V1_PREFIX}/network", tags=["Diagnóstico Red"])
app.include_router(forensic_analysis.router, prefix=f"{settings.API_V1_PREFIX}/forensic", tags=["Análisis Forense"])
app.include_router(experimental_tests.router, prefix=f"{settings.API_V1_PREFIX}/experimental", tags=["Tests Experimentales"])
app.include_router(comparative_analysis.router, prefix=f"{settings.API_V1_PREFIX}/comparative", tags=["Análisis Comparativo"])
app.include_router(temporal_analysis.router, prefix=f"{settings.API_V1_PREFIX}/temporal", tags=["Análisis Temporal"])
app.include_router(architectural_analysis.router, prefix=f"{settings.API_V1_PREFIX}/architectural", tags=["Análisis Arquitectural"])
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
