"""
"""
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

# Routers
from app.api.v1.endpoints import 
from app.core.config import settings
from app.db.init_db import init_db_shutdown, init_db_startup

# Rate Limiting

# Configurar logging básico pero efectivo
logging.basicConfig
    level=getattr(logging, settings.LOG_LEVEL),
    handlers=[
        logging.StreamHandler(sys.stdout),  # Asegurar que vaya a stdout
    ],
    force=True,  # Forzar reconfiguración

logger = logging.getLogger(__name__)

app_logger = logging.getLogger("app")
app_logger.setLevel(getattr(logging, settings.LOG_LEVEL))
app_logger.handlers.clear()
app_logger.addHandler(logging.StreamHandler(sys.stdout))

# Log de inicio
logger.info
logger.info
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
        response.headers["Content-Security-Policy"] = 

        # Referrer Policy más permisivo
        response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"

        # Permissions Policy más permisivo
        response.headers["Permissions-Policy"] = 

        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida"""
    init_db_startup()
    yield
    init_db_shutdown()


app = FastAPI

# Configurar rate limiter en app state - TEMPORALMENTE DESACTIVADO
# app.state.limiter = limiter
# app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ============================================
# MIDDLEWARES DE SEGURIDAD
# ============================================

# Security Headers - OWASP Best Practices
app.add_middleware(SecurityHeadersMiddleware)

# CORS - MIDDLEWARE SIMPLE PARA OPTIONS
logger.info

# MIDDLEWARE CORS CENTRALIZADO - USANDO CONFIGURACIÓN DE SETTINGS
app.add_middleware

# Registrar routers
app.include_router
app.include_router
app.include_router
app.include_router
app.include_router
app.include_router
app.include_router
app.include_router
app.include_router
app.include_router
app.include_router
app.include_router
app.include_router
app.include_router
app.include_router
app.include_router
app.include_router
app.include_router
app.include_router
app.include_router
app.include_router
app.include_router
app.include_router
app.include_router
app.include_router
app.include_router
app.include_router

# app.include_router
@app.get("/", include_in_schema=False)
async def root():
    return 

"""
"""