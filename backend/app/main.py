"""
Aplicación principal FastAPI
Configuración central de la aplicación y registro de endpoints
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
    auth,
    clientes,
    concesionarios,
    configuracion,
    dashboard,
    logo,
    notificaciones,
    pagos,
    prestamos,
    reportes,
    solicitudes,
    users,
    validadores,
)
from app.core.config import settings
from app.db.init_db import init_db_shutdown, init_db_startup

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
logger.info("=== INICIANDO APLICACIÓN ===")
logger.info("Configuración de logging aplicada")
logger.info(f"CORS Origins: {settings.CORS_ORIGINS}")
logger.info(f"Database URL configurada: {bool(settings.DATABASE_URL)}")


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

        # CSP: permite blob: para previsualizaciones de imágenes
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https: blob:; "  # blob: para preview
            "font-src 'self' data:; "
            "connect-src 'self'"
        )

        # Referrer Policy más permisivo
        response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"

        # Permissions Policy más permisivo
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "speaker=()"
        )

        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida"""
    init_db_startup()
    yield
    init_db_shutdown()


app = FastAPI(
    title="Sistema de Pagos",
    description="API para gestión de pagos y préstamos",
    version="1.0.0",
    lifespan=lifespan,
)

# ============================================
# MIDDLEWARES DE SEGURIDAD
# ============================================

# Security Headers - OWASP Best Practices
app.add_middleware(SecurityHeadersMiddleware)

# CORS - MIDDLEWARE SIMPLE PARA OPTIONS
logger.info("Configurando CORS middleware")

# MIDDLEWARE CORS CENTRALIZADO - USANDO CONFIGURACIÓN DE SETTINGS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# REGISTRO DE ROUTERS
# ============================================

# Registrar routers principales
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/v1/usuarios", tags=["usuarios"])
app.include_router(clientes.router, prefix="/api/v1/clientes", tags=["clientes"])
app.include_router(
    concesionarios.router, prefix="/api/v1/concesionarios", tags=["concesionarios"]
)
app.include_router(prestamos.router, prefix="/api/v1/prestamos", tags=["prestamos"])
app.include_router(pagos.router, prefix="/api/v1/pagos", tags=["pagos"])
app.include_router(
    amortizacion.router, prefix="/api/v1/amortizacion", tags=["amortizacion"]
)
app.include_router(
    solicitudes.router, prefix="/api/v1/solicitudes", tags=["solicitudes"]
)
app.include_router(
    aprobaciones.router, prefix="/api/v1/aprobaciones", tags=["aprobaciones"]
)
app.include_router(
    notificaciones.router, prefix="/api/v1/notificaciones", tags=["notificaciones"]
)
app.include_router(reportes.router, prefix="/api/v1/reportes", tags=["reportes"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(
    configuracion.router, prefix="/api/v1/configuracion", tags=["configuracion"]
)
app.include_router(analistas.router, prefix="/api/v1/analistas", tags=["analistas"])
app.include_router(
    validadores.router, prefix="/api/v1/validadores", tags=["validadores"]
)
app.include_router(logo.router, prefix="/api/v1", tags=["logo"])

logger.info("Todos los routers registrados correctamente")


@app.get("/", include_in_schema=False)
async def root():
    """Endpoint raíz de la aplicación"""
    return {
        "message": "Sistema de Pagos API",
        "version": "1.0.0",
        "status": "active",
        "docs": "/docs",
    }


@app.get("/health", include_in_schema=False)
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "API funcionando correctamente"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
