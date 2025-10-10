from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.api.v1.endpoints import health, clientes, prestamos, pagos


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manejo del ciclo de vida de la aplicación.
    Reemplaza @app.on_event("startup") y @app.on_event("shutdown")
    """
    # STARTUP
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} iniciado")
    print(f"📝 Documentación disponible en: /docs")
    print(f"🌍 Entorno: {settings.ENVIRONMENT}")
    
    yield  # La aplicación está corriendo
    
    # SHUTDOWN
    print(f"🛑 {settings.APP_NAME} detenido")


# Crear aplicación
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Microservicio de Gestión de Pagos",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,  # ✅ Nuevo: usar lifespan en lugar de on_event
)


# Middleware para manejo global de errores
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Captura todas las excepciones no manejadas"""
    print(f"❌ Error no manejado: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Error interno del servidor",
            "error": str(exc) if settings.DEBUG else "Internal Server Error"
        }
    )


# Configurar CORS
if settings.ALLOWED_ORIGINS and settings.ALLOWED_ORIGINS != ["*"]:
    # Configuración segura con orígenes específicos
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # Configuración permisiva para desarrollo
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,  # ✅ No permitir credentials con wildcard
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Incluir routers
app.include_router(health.router, tags=["Health"])
app.include_router(
    clientes.router,
    prefix=f"{settings.API_PREFIX}/clientes",
    tags=["Clientes"]
)
app.include_router(
    prestamos.router,
    prefix=f"{settings.API_PREFIX}/prestamos",
    tags=["Préstamos"]
)
app.include_router(
    pagos.router,
    prefix=f"{settings.API_PREFIX}/pagos",
    tags=["Pagos"]
)


# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Endpoint raíz - redirige a documentación"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health"
    }
