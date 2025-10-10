from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.v1.endpoints import health, clientes, prestamos, pagos

# Crear aplicación
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Microservicio de Gestión de Pagos",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
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


@app.on_event("startup")
async def startup_event():
    """Evento ejecutado al iniciar la aplicación"""
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} iniciado")
    print(f"📝 Documentación disponible en: /docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Evento ejecutado al detener la aplicación"""
    print(f"🛑 {settings.APP_NAME} detenido")
