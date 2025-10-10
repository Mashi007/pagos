# backend/app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os

# ✅ Importar endpoints existentes SOLAMENTE
from app.api.v1.endpoints import health, clientes, prestamos, pagos


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manejo del ciclo de vida de la aplicación.
    """
    from app.config import get_settings
    from app.db.session import init_db
    
    settings = get_settings()
    
    try:
        init_db()
        print("=" * 50)
        print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION}")
        print("=" * 50)
        print(f"🗄️  Base de datos: {settings.DATABASE_URL[:30]}...")
        print("✅ Base de datos inicializada correctamente")
        print(f"🌍 Entorno: {settings.ENVIRONMENT}")
        print(f"📝 Documentación: /docs")
        print("=" * 50)
    except Exception as e:
        print(f"❌ Error al inicializar BD: {e}")
        raise
    
    yield
    
    print(f"🛑 {settings.APP_NAME} detenido")


app = FastAPI(
    title=os.getenv("APP_NAME", "Sistema de Préstamos y Cobranza"),
    version=os.getenv("APP_VERSION", "1.0.0"),
    description="Sistema completo de gestión de préstamos, cobranza y pagos",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Captura todas las excepciones no manejadas"""
    debug = os.getenv("DEBUG", "false").lower() == "true"
    print(f"❌ Error no manejado: {exc}")
    
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


# CORS
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


# Routers
api_prefix = os.getenv("API_PREFIX", "/api/v1")

app.include_router(health.router, tags=["Health"])

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


@app.get("/", include_in_schema=False)
async def root():
    """Endpoint raíz"""
    return {
        "app": os.getenv("APP_NAME", "Sistema de Préstamos y Cobranza"),
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }
