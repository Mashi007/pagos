"""
Aplicación principal FastAPI
Configuración central de la aplicación y registro de endpoints
"""

import logging
import sys
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# IMPORTANTE: Configurar logging ANTES de importar otros módulos que usan logging
# Esto asegura que los logs de inicialización (como cache) se muestren correctamente
from app.core.config import settings

# Configurar logging básico pero efectivo
# Evitar duplicación: limpiar handlers existentes antes de configurar
root_logger = logging.getLogger()
root_logger.handlers.clear()

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    handlers=[
        logging.StreamHandler(sys.stdout),  # Asegurar que vaya a stdout
    ],
    force=True,  # Forzar reconfiguración
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

# Routers
# Imports después de logging por diseño - ver comentario arriba
from app.api.v1.endpoints import (  # noqa: E402
    amortizacion,
    analistas,
    # aprobaciones,  # MODULO APROBACIONES DESHABILITADO
    auditoria,
    auth,
    carga_masiva,
    clientes,
    cobranzas,
    concesionarios,
    conciliacion_bancaria,
    configuracion,
    dashboard,
    health,
    kpis,
    modelos_vehiculos,
    monitoring,
    notificaciones,
    notificaciones_previas,
    pagos,
    pagos_conciliacion,
    pagos_upload,
    prestamos,
    reportes,
    scheduler_notificaciones,
    solicitudes,
    users,
    validadores,
)

# Forzar inicialización de cache DESPUÉS de configurar logging
# Ahora los logs de inicialización del cache se mostrarán correctamente
from app.core import cache  # noqa: F401, E402
from app.core.exceptions import global_exception_handler  # noqa: E402
from app.core.performance_monitor import performance_monitor  # noqa: E402
from app.db.init_db import init_db_shutdown, init_db_startup  # noqa: E402

# No crear otro logger duplicado - usar el root logger o el logger del módulo
# app_logger removido para evitar duplicación

# Log de inicio
logger.info("=== INICIANDO APLICACIÓN ===")
logger.info("Configuración de logging aplicada")
logger.info(f"CORS Origins: {settings.CORS_ORIGINS}")
logger.info(f"Database URL configurada: {bool(settings.DATABASE_URL)}")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware para agregar Request ID único a cada request
    Facilita correlación de logs y debugging
    """

    async def dispatch(self, request: Request, call_next):
        # Generar Request ID único
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Procesar request
        response = await call_next(request)

        # Agregar Request ID al header de respuesta
        response.headers["X-Request-ID"] = request_id

        return response


class PerformanceLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware para registrar tiempo de respuesta de las peticiones
    Loggea información útil para monitoreo y debugging de rendimiento
    """

    async def dispatch(self, request: Request, call_next):
        # Obtener request ID si existe
        request_id = getattr(request.state, "request_id", None)

        # Obtener IP del cliente
        client_ip = request.client.host if request.client else "unknown"

        # Obtener user agent
        user_agent = request.headers.get("user-agent", "unknown")

        # Iniciar timer
        start_time = time.time()

        # Procesar request
        response = await call_next(request)

        # Calcular tiempo de respuesta en milisegundos
        response_time_ms = int((time.time() - start_time) * 1000)

        # Obtener tamaño de respuesta del header Content-Length si está disponible
        content_length = response.headers.get("content-length")
        response_bytes = int(content_length) if content_length else 0

        # Determinar nivel de log según tiempo de respuesta
        if response_time_ms > 5000:  # > 5 segundos
            log_level = logging.ERROR
            emoji = "🐌"
        elif response_time_ms > 2000:  # > 2 segundos
            log_level = logging.WARNING
            emoji = "⚠️"
        elif response_time_ms > 1000:  # > 1 segundo
            log_level = logging.INFO
            emoji = "⏱️"
        else:
            log_level = logging.DEBUG
            emoji = "✅"

        # Log estructurado compatible con formato de Render
        logger.log(
            log_level,
            f"{emoji} {request.method} {request.url.path} - "
            f"responseTimeMS={response_time_ms} "
            f"responseBytes={response_bytes} "
            f"status={response.status_code} "
            f'requestID="{request_id}" '
            f'clientIP="{client_ip}" '
            f'userAgent="{user_agent}"',
        )

        # Registrar en el monitor de performance
        try:
            performance_monitor.record_request(
                method=request.method,
                path=request.url.path,
                response_time_ms=response_time_ms,
                status_code=response.status_code,
                response_bytes=response_bytes,
            )
        except Exception as e:
            logger.warning(f"Error registrando métrica en monitor: {e}")

        # Agregar headers de performance
        response.headers["X-Response-Time-Ms"] = str(response_time_ms)

        return response


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

        # CSP para seguridad
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
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

    # Iniciar scheduler para tareas automáticas
    from app.core import scheduler as scheduler_module

    scheduler_module.iniciar_scheduler()

    yield

    # Detener scheduler al cerrar
    scheduler_module.detener_scheduler()
    init_db_shutdown()


app = FastAPI(
    title="Sistema de Pagos",
    description="API para gestión de pagos y préstamos",
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=False,  # Desactivar redirects automáticos de barras finales
)

# Registrar manejador global de excepciones
app.add_exception_handler(Exception, global_exception_handler)

# ============================================
# MIDDLEWARES
# ============================================

# Request ID - Para correlación de logs (debe ir primero)
app.add_middleware(RequestIDMiddleware)

# Performance Logging - Registrar tiempos de respuesta (después de RequestID)
app.add_middleware(PerformanceLoggingMiddleware)

# Compresión GZip - Para optimizar tamaño de respuestas
app.add_middleware(GZipMiddleware, minimum_size=1000)

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
# Concesionarios movido después junto con analistas y modelos_vehiculos
app.include_router(prestamos.router, prefix="/api/v1/prestamos", tags=["prestamos"])
app.include_router(pagos.router, prefix="/api/v1/pagos", tags=["pagos"])
app.include_router(pagos_upload.router, prefix="/api/v1/pagos", tags=["pagos"])
app.include_router(pagos_conciliacion.router, prefix="/api/v1/pagos", tags=["pagos"])
app.include_router(amortizacion.router, prefix="/api/v1/amortizacion", tags=["amortizacion"])
app.include_router(solicitudes.router, prefix="/api/v1/solicitudes", tags=["solicitudes"])
# MODULO APROBACIONES DESHABILITADO
# app.include_router(aprobaciones.router, prefix="/api/v1/aprobaciones", tags=["aprobaciones"])
app.include_router(notificaciones.router, prefix="/api/v1/notificaciones", tags=["notificaciones"])
app.include_router(notificaciones_previas.router, prefix="/api/v1/notificaciones-previas", tags=["notificaciones-previas"])

# Importar router de notificaciones del día de pago
from app.api.v1.endpoints import notificaciones_dia_pago  # noqa: E402

app.include_router(notificaciones_dia_pago.router, prefix="/api/v1/notificaciones-dia-pago", tags=["notificaciones-dia-pago"])

# Importar router de notificaciones retrasadas
from app.api.v1.endpoints import notificaciones_retrasadas  # noqa: E402

app.include_router(
    notificaciones_retrasadas.router, prefix="/api/v1/notificaciones-retrasadas", tags=["notificaciones-retrasadas"]
)

# Importar router de notificaciones prejudiciales
from app.api.v1.endpoints import notificaciones_prejudicial  # noqa: E402

app.include_router(
    notificaciones_prejudicial.router, prefix="/api/v1/notificaciones-prejudicial", tags=["notificaciones-prejudicial"]
)
app.include_router(reportes.router, prefix="/api/v1/reportes", tags=["reportes"])
app.include_router(cobranzas.router, prefix="/api/v1/cobranzas", tags=["cobranzas"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(kpis.router, prefix="/api/v1/kpis", tags=["kpis"])
app.include_router(auditoria.router, prefix="/api/v1", tags=["auditoria"])
app.include_router(configuracion.router, prefix="/api/v1/configuracion", tags=["configuracion"])
# IMPORTANTE: Registrar estos routers ANTES de otros para evitar conflictos de rutas
# Orden: modelos_vehiculos → analistas → concesionarios
app.include_router(
    modelos_vehiculos.router,
    prefix="/api/v1/modelos-vehiculos",
    tags=["modelos-vehiculos"],
)
app.include_router(analistas.router, prefix="/api/v1/analistas", tags=["analistas"])
app.include_router(concesionarios.router, prefix="/api/v1/concesionarios", tags=["concesionarios"])
app.include_router(validadores.router, prefix="/api/v1/validadores", tags=["validadores"])
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(monitoring.router, prefix="/api/v1/monitoring", tags=["monitoring"])
app.include_router(carga_masiva.router, prefix="/api/v1/carga-masiva", tags=["carga-masiva"])
app.include_router(conciliacion_bancaria.router, prefix="/api/v1/conciliacion", tags=["conciliacion"])
app.include_router(scheduler_notificaciones.router, prefix="/api/v1/scheduler", tags=["scheduler"])

# Log detallado de rutas registradas
logger.info("✅ Todos los routers registrados correctamente")
logger.info("📋 Router modelos_vehiculos registrado con prefix: /api/v1/modelos-vehiculos")
logger.info("📋 Router analistas registrado con prefix: /api/v1/analistas")
logger.info("📋 Router concesionarios registrado con prefix: /api/v1/concesionarios")


@app.get("/", include_in_schema=False)
@app.head("/", include_in_schema=False)
async def root():
    """Endpoint raíz de la aplicación"""
    return {
        "message": "Sistema de Pagos API",
        "version": "1.0.0",
        "status": "active",
        "docs": "/docs",
    }


@app.get("/health", include_in_schema=False)
@app.head("/health", include_in_schema=False)
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "API funcionando correctamente"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
