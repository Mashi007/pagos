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

# Configurar logging estructurado JSON para producción, texto para desarrollo
# Evitar duplicación: limpiar handlers existentes antes de configurar
root_logger = logging.getLogger()
root_logger.handlers.clear()

# Determinar si usar logging estructurado JSON
use_json_logging = settings.ENVIRONMENT == "production"

if use_json_logging:
    # Logging estructurado JSON para producción
    try:
        from pythonjsonlogger import jsonlogger

        class CustomJsonFormatter(jsonlogger.JsonFormatter):
            """Formatter JSON personalizado con campos adicionales"""

            def add_fields(self, log_record, record, message_dict):
                super().add_fields(log_record, record, message_dict)
                log_record["timestamp"] = self.formatTime(record, self.datefmt)
                log_record["level"] = record.levelname
                log_record["logger"] = record.name
                log_record["environment"] = settings.ENVIRONMENT

        json_formatter = CustomJsonFormatter("%(timestamp)s %(level)s %(logger)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(json_formatter)

        logging.basicConfig(
            level=getattr(logging, settings.LOG_LEVEL),
            handlers=[handler],
            force=True,
        )
        logger = logging.getLogger(__name__)
        logger.info("✅ Logging estructurado JSON configurado para producción")
    except ImportError:
        # Si python-json-logger no está disponible, usar formato texto
        use_json_logging = False
        logging.warning("⚠️ python-json-logger no disponible. Usando formato texto.")

if not use_json_logging:
    # Logging en formato texto para desarrollo
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        handlers=[
            logging.StreamHandler(sys.stdout),  # Asegurar que vaya a stdout
        ],
        force=True,  # Forzar reconfiguración
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

logger = logging.getLogger(__name__)

# ============================================
# SENTRY MONITORING (Opcional)
# ============================================
# ✅ MEJORA 2025-01-27: Integración de Sentry para monitoreo de errores
# Solo se inicializa si SENTRY_DSN está configurado
try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            traces_sample_rate=0.1 if settings.ENVIRONMENT == "production" else 1.0,
            profiles_sample_rate=0.1 if settings.ENVIRONMENT == "production" else 1.0,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
                LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
            ],
            release=f"pagos-api@{settings.APP_VERSION}",
        )
        logger.info("✅ Sentry inicializado para monitoreo de errores")
    else:
        logger.debug("Sentry no configurado (SENTRY_DSN no está configurado)")
except ImportError:
    logger.debug("Sentry no disponible (sentry-sdk no instalado)")
except Exception as e:
    logger.warning(f"⚠️ Error al inicializar Sentry: {e}")

# Routers
# Imports después de logging por diseño - ver comentario arriba
from app.api.v1.endpoints import (  # noqa: E402; aprobaciones deshabilitado - ver __init__.py
    ai_training,
    amortizacion,
    analistas,
    auditoria,
    auth,
    carga_masiva,
    clientes,
    cobranzas,
    comunicaciones,
    concesionarios,
    conciliacion_bancaria,
    configuracion,
    conversaciones_whatsapp,
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
    tickets,
    users,
    validadores,
    whatsapp_webhook,
)

# Forzar inicialización de cache DESPUÉS de configurar logging
# Ahora los logs de inicialización del cache se mostrarán correctamente
from app.core import cache  # noqa: F401, E402
from app.core.exceptions import global_exception_handler  # noqa: E402
from app.core.performance_monitor import performance_monitor  # noqa: E402
from app.core.rate_limiter import (  # noqa: E402
    get_rate_limit_exceeded_handler,
    get_rate_limiter,
)
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

        # ✅ DIAGNÓSTICO: Detectar requests lentos y registrar información adicional
        if response_time_ms > 2000:
            # Categorizar según severidad
            if response_time_ms > 5000:
                log_level = logging.ERROR
                emoji_severity = "🚨"
                severity = "CRÍTICO"
            elif response_time_ms > 3000:
                log_level = logging.WARNING
                emoji_severity = "⚠️"
                severity = "MUY LENTO"
            else:
                log_level = logging.WARNING
                emoji_severity = "🐌"
                severity = "LENTO"

            logger.log(
                log_level,
                f"{emoji_severity} [SLOW REQUEST - {severity}] {request.method} {request.url.path} - "
                f"responseTimeMS={response_time_ms}ms - "
                f"responseBytes={response_bytes} - "
                f"status={response.status_code} - "
                f'requestID="{request_id}" - '
                f'queryParams="{request.url.query}" - '
                f"💡 Considerar optimizar queries o agregar índices",
            )

        # ✅ DIAGNÓSTICO: Detectar respuestas muy pequeñas que podrían indicar errores o datos vacíos
        # Respuestas pequeñas (< 1500 bytes) en endpoints de API que normalmente retornan datos
        if response_bytes > 0 and response_bytes < 1500 and response.status_code == 200:
            # Solo alertar en endpoints de API, no en assets estáticos
            if request.url.path.startswith("/api/"):
                # Determinar si es un endpoint que normalmente retorna datos grandes
                endpoints_con_datos = [
                    "/api/v1/dashboard",
                    "/api/v1/pagos/kpis",
                    "/api/v1/notificaciones/estadisticas",
                    "/api/v1/clientes",
                    "/api/v1/prestamos",
                ]
                es_endpoint_con_datos = any(request.url.path.startswith(ep) for ep in endpoints_con_datos)

                if es_endpoint_con_datos:
                    # Cambiar a INFO en lugar de WARNING - respuestas pequeñas pueden ser válidas (sin datos)
                    logger.info(
                        f"ℹ️ [SMALL RESPONSE] {request.method} {request.url.path} - "
                        f"responseBytes={response_bytes} - "
                        f"responseTimeMS={response_time_ms}ms - "
                        f'requestID="{request_id}" - '
                        f'queryParams="{request.url.query}" - '
                        f"ℹ️ Respuesta pequeña (posiblemente sin datos) - Comportamiento normal si no hay registros"
                    )
                else:
                    logger.debug(
                        f"📦 [SMALL RESPONSE] {request.method} {request.url.path} - "
                        f"responseBytes={response_bytes} - "
                        f"responseTimeMS={response_time_ms}ms"
                    )

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
# RATE LIMITING
# ============================================
# Importar RateLimitExceeded antes de usarlo
from slowapi.errors import RateLimitExceeded  # noqa: E402

# Configurar rate limiting para proteger contra abuso
limiter = get_rate_limiter()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, get_rate_limit_exceeded_handler())

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
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
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
app.include_router(ai_training.router, prefix="/api/v1/ai/training", tags=["ai-training"])
app.include_router(whatsapp_webhook.router, prefix="/api/v1", tags=["whatsapp-webhook"])
app.include_router(conversaciones_whatsapp.router, prefix="/api/v1", tags=["conversaciones-whatsapp"])
app.include_router(comunicaciones.router, prefix="/api/v1", tags=["comunicaciones"])
app.include_router(tickets.router, prefix="/api/v1", tags=["tickets"])
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
