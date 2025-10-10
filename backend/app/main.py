# backend/app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os

# ✅ Importar endpoints existentes
from app.api.v1.endpoints import health, clientes, prestamos, pagos
# ✅ NUEVO: Importar endpoint de autenticación
from app.api.v1 import auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manejo del ciclo de vida de la aplicación.
    Reemplaza @app.on_event("startup") y @app.on_event("shutdown")
    """
    # ✅ STARTUP - Cargar settings AQUÍ, no al inicio del archivo
    from app.config import get_settings
    from app.db.session import init_db
    
    # Obtener settings
    settings = get_settings()
    
    # Inicializar base de datos
    try:
        init_db()
        print("=" * 50)
        print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION}")
        print("=" * 50)
        print(f"🗄️  Base de datos: {settings.DATABASE_URL[:30]}...")
        print("✅ Base de datos inicializada correctamente")
        print(f"🌍 Entorno: {settings.ENVIRONMENT}")
        print(f"🔐 Autenticación: JWT habilitada")
        print(f"📝 Documentación: /docs")
        print("=" * 50)
    except Exception as e:
        print(f"❌ Error al inicializar BD: {e}")
        raise
    
    yield  # La aplicación está corriendo
    
    # SHUTDOWN
    print(f"🛑 {settings.APP_NAME} detenido")


# ✅ Crear aplicación SIN cargar settings aún
app = FastAPI(
    title=os.getenv("APP_NAME", "Sistema de Préstamos y Cobranza"),
    version=os.getenv("APP_VERSION", "1.0.0"),
    description="Sistema completo de gestión de préstamos, cobranza y pagos",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# Middleware para manejo global de errores
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Captura todas las excepciones no manejadas"""
    debug = os.getenv("DEBUG", "false").lower() == "true"
    print(f"❌ Error no manejado: {exc}")
    
    # Registrar en logs
    import traceback
    if debug:
        traceback.print_exc()
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Error interno del servidor",
            "error": str(exc) if debug else "Internal Server Error"
        }
    )


# ✅ Configurar CORS - Leer desde ENV directamente
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
if allowed_origins != ["*"]:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# ✅ Incluir routers - Leer API_PREFIX desde ENV
api_prefix = os.getenv("API_PREFIX", "/api/v1")

# Health check (sin autenticación)
app.include_router(health.router, tags=["Health"])

# ✅ NUEVO: Autenticación (sin prefijo /api/v1)
app.include_router(
    auth.router,
    prefix="/auth",
    tags=["Autenticación"]
)

# ✅ Endpoints protegidos (requieren JWT)
app.include_router(
    clientes.router,
    prefix=f"{api_prefix}/clientes",
    tags=["Clientes"]
)

app.include_router(
    prestamos.router,
    prefix=f"{api_prefix}/prestamos",
    tags=["Préstamos"]
)

app.include_router(
    pagos.router,
    prefix=f"{api_prefix}/pagos",
    tags=["Pagos"]
)


# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Endpoint raíz - información de la API"""
    return {
        "app": os.getenv("APP_NAME", "Sistema de Préstamos y Cobranza"),
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "status": "running",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "auth": {
                "login": "/auth/login",
                "refresh": "/auth/refresh",
                "me": "/auth/me"
            },
            "api": api_prefix
        }
    }


# Endpoint de información de la API
@app.get("/info", include_in_schema=False)
async def api_info():
    """Información detallada de la API"""
    return {
        "name": os.getenv("APP_NAME", "Sistema de Préstamos y Cobranza"),
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "environment": os.getenv("ENVIRONMENT", "production"),
        "features": [
            "Gestión de clientes",
            "Gestión de préstamos",
            "Registro de pagos",
            "Autenticación JWT",
            "Sistema de roles y permisos",
            "Auditoría de operaciones"
        ],
        "authentication": {
            "type": "JWT Bearer Token",
            "endpoints": {
                "login": "/auth/login",
                "refresh": "/auth/refresh",
                "profile": "/auth/me",
                "verify": "/auth/verify"
            }
        }
    }
