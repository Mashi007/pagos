# backend/app/main.py
"""
Aplicación principal FastAPI - Sistema de Préstamos y Cobranza.
Incluye TODOS los módulos implementados.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.db.init_db import init_db, check_database_connection

# ✅ CORRECTO: Importar routers directamente desde cada archivo
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.clientes import router as clientes_router
from app.api.v1.endpoints.prestamos import router as prestamos_router
from app.api.v1.endpoints.pagos import router as pagos_router
from app.api.v1.endpoints.conciliacion import router as conciliacion_router
from app.api.v1.endpoints.reportes import router as reportes_router
from app.api.v1.endpoints.kpis import router as kpis_router
from app.api.v1.endpoints.notificaciones import router as notificaciones_router
from app.api.v1.endpoints.aprobaciones import router as aprobaciones_router
from app.api.v1.endpoints.auditoria import router as auditoria_router
from app.api.v1.endpoints.configuracion import router as configuracion_router

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida de la aplicación"""
    # Startup
    logger.info("="*50)
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("="*50)
    logger.info(f"🗄️  Base de datos: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'N/A'}")
    
    # Inicializar base de datos
    init_db()
    logger.info("✅ Base de datos inicializada correctamente")
    
    # Verificar conexión
    if check_database_connection():
        logger.info("✅ Conexión a base de datos verificada")
    else:
        logger.error("❌ Error en conexión a base de datos")
    
    logger.info(f"🌍 Entorno: {settings.ENVIRONMENT}")
    logger.info(f"📝 Documentación: /docs")
    logger.info(f"🔧 Debug mode: {'ON' if settings.DEBUG else 'OFF'}")
    logger.info("="*50)
    
    yield
    
    # Shutdown
    logger.info("🛑 Sistema de Préstamos y Cobranza detenido")


# Crear aplicación
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API completa para gestión de préstamos, cobranza y pagos",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(",") if settings.ALLOWED_ORIGINS != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# REGISTRAR ROUTERS
# ============================================

# Health check
app.include_router(
    health_router,
    tags=["Health"]
)

# Módulos principales
app.include_router(
    clientes_router,
    prefix=f"{settings.API_V1_PREFIX}/clientes",
    tags=["Clientes"]
)

app.include_router(
    prestamos_router,
    prefix=f"{settings.API_V1_PREFIX}/prestamos",
    tags=["Préstamos"]
)

app.include_router(
    pagos_router,
    prefix=f"{settings.API_V1_PREFIX}/pagos",
    tags=["Pagos"]
)

# Conciliación bancaria
app.include_router(
    conciliacion_router,
    prefix=f"{settings.API_V1_PREFIX}/conciliacion",
    tags=["Conciliación Bancaria"]
)

# Reportes
app.include_router(
    reportes_router,
    prefix=f"{settings.API_V1_PREFIX}/reportes",
    tags=["Reportes"]
)

# KPIs y Estadísticas
app.include_router(
    kpis_router,
    prefix=f"{settings.API_V1_PREFIX}/kpis",
    tags=["KPIs y Métricas"]
)

# Notificaciones
app.include_router(
    notificaciones_router,
    prefix=f"{settings.API_V1_PREFIX}/notificaciones",
    tags=["Notificaciones"]
)

# Sistema de aprobaciones
app.include_router(
    aprobaciones_router,
    prefix=f"{settings.API_V1_PREFIX}/aprobaciones",
    tags=["Aprobaciones"]
)

# Auditoría
app.include_router(
    auditoria_router,
    prefix=f"{settings.API_V1_PREFIX}/auditoria",
    tags=["Auditoría"]
)

# Configuración administrativa
app.include_router(
    configuracion_router,
    prefix=f"{settings.API_V1_PREFIX}/configuracion",
    tags=["Configuración"]
)


@app.get("/", include_in_schema=False)
async def root():
    """Endpoint raíz con información del sistema"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "clientes": f"{settings.API_V1_PREFIX}/clientes",
            "prestamos": f"{settings.API_V1_PREFIX}/prestamos",
            "pagos": f"{settings.API_V1_PREFIX}/pagos",
            "conciliacion": f"{settings.API_V1_PREFIX}/conciliacion",
            "reportes": f"{settings.API_V1_PREFIX}/reportes",
            "kpis": f"{settings.API_V1_PREFIX}/kpis",
            "notificaciones": f"{settings.API_V1_PREFIX}/notificaciones",
            "aprobaciones": f"{settings.API_V1_PREFIX}/aprobaciones",
            "auditoria": f"{settings.API_V1_PREFIX}/auditoria",
            "configuracion": f"{settings.API_V1_PREFIX}/configuracion"
        }
    }


# Manejo global de excepciones
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Captura todas las excepciones no manejadas"""
    logger.error(f"❌ Error no manejado: {exc}", exc_info=True)
    
    return {
        "detail": "Error interno del servidor",
        "error": str(exc) if settings.DEBUG else "Internal Server Error",
        "type": type(exc).__name__
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=settings.DEBUG
    )
