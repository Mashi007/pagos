# backend/app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os

# ✅ Importar TODOS los endpoints existentes
from app.api.v1.endpoints import (
    health,
    clientes,
    prestamos,
    pagos,
    auth,
    users,
    amortizacion,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manejo del ciclo de vida de la aplicación.
    """
    from app.config import get_settings
    from app.db.init_db import init_database, check_database_connection
    
    settings = get_settings()
    
    # Startup
    print("\n" + "=" * 50)
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION}")
    print("=" * 50)
    
    # Mostrar DATABASE_URL (ocultando contraseña)
    db_url_safe = settings.get_database_url(hide_password=True)
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
    from app.config import get_settings
    settings = get_settings()
    
    print(f"❌ Error no manejado: {exc}")
    
    import traceback
    if settings.DEBUG:
        traceback.print_exc()
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Error interno del servidor",
            "error": str(exc) if settings.DEBUG else "Internal Server Error"
        }
    )


# CORS
from app.config import get_settings
settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True if settings.allowed_origins_list != ["*"] else False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# ROUTERS
# ============================================
api_prefix = os.getenv("API_PREFIX", "/api/v1")

# Health Check (sin prefijo)
app.include_router(
    health.router,
    tags=["Health"]
)

# Autenticación (sin autenticación requerida)
app.include_router(
    auth.router,
    prefix=f"{api_prefix}/auth",
    tags=["Autenticación"]
)

# Usuarios (requiere autenticación - configurado en el router)
app.include_router(
    users.router,
    prefix=f"{api_prefix}/users",
    tags=["Usuarios"]
)

# Clientes
app.include_router(
    clientes.router,
    prefix=f"{api_prefix}/clientes",
    tags=["Clientes"]
)

# Préstamos
app.include_router(
    prestamos.router,
    prefix=f"{api_prefix}/prestamos",
    tags=["Préstamos"]
)

# Pagos
app.include_router(
    pagos.router,
    prefix=f"{api_prefix}/pagos",
    tags=["Pagos"]
)

# Amortización
app.include_router(
    amortizacion.router,
    prefix=f"{api_prefix}/amortizacion",
    tags=["Amortización"]
)


@app.get("/", include_in_schema=False)
async def root():
    """Endpoint raíz con información del sistema"""
    from app.config import get_settings
    settings = get_settings()
    
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "api": {
            "v1": api_prefix
        },
        "endpoints": {
            "auth": f"{api_prefix}/auth",
            "users": f"{api_prefix}/users",
            "clientes": f"{api_prefix}/clientes",
            "prestamos": f"{api_prefix}/prestamos",
            "pagos": f"{api_prefix}/pagos",
            "amortizacion": f"{api_prefix}/amortizacion",
        }
    }
