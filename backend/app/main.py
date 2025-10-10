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
    from app.db.init_db import init_database, check_database_connection  # ✅ CORRECCIÓN
    
    settings = get_settings()
    
    # Startup
    print("\n" + "=" * 50)
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION}")
    print("=" * 50)
    
    # Mostrar DATABASE_URL (ocultando contraseña)
    db_url = settings.DATABASE_URL
    if '@' in db_url:
        parts = db_url.split('@')
        user_part = parts[0].split('://')
        if len(user_part) > 1:
            protocol = user_part[0]
            user = user_part[1].split(':')[0]
            db_url_safe = f"{protocol}://{user}:***@{parts[1]}"
        else:
            db_url_safe = "***"
    else:
        db_url_safe = "No configurada"
    
    print(f"🗄️  Base de datos: {db_url_safe}")
    
    # Inicializar tablas
    try:
        if init_database():
            print("✅ Base de datos inicializada correctamente")
        else:
            print("⚠️  Advertencia: Error inicializando tablas")
    except Exception as e:
        print(f"❌ Error al inicializar BD: {e}")
        import traceback
        if settings.DEBUG:
            traceback.print_exc()
    
    # Verificar conexión
    if check_database_connection():
        print("✅ Conexión a base de datos verificada")
    else:
        print("❌ Error: No se pudo conectar a la base de datos")
    
    print(f"🌍 Entorno: {settings.ENVIRONMENT}")
    print(f"📝 Documentación: /docs")
    print(f"🔧 Debug mode: {'ON' if settings.DEBUG else 'OFF'}")
    print("=" * 50 + "\n")
    
    yield
    
    # Shutdown
    print(f"\n🛑 {settings.APP_NAME} detenido")


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
    from app.config import get_settings
    settings = get_settings()
    
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }
