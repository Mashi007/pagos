# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import logging

from app.config import settings
from app.api.v1.endpoints import health, clientes, prestamos, pagos

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Crear aplicación FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="API REST para gestión de préstamos, pagos y cobranza",
    docs_url="/docs",
    redoc_url="/redoc"
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
app.include_router(clientes.router, prefix="/api/v1/clientes", tags=["Clientes"])
app.include_router(prestamos.router, prefix="/api/v1/prestamos", tags=["Préstamos"])
app.include_router(pagos.router, prefix="/api/v1/pagos", tags=["Pagos"])

@app.on_event("startup")
async def startup_event():
    """Evento de inicio"""
    logger.info("=" * 50)
    logger.info(f"🚀 {settings.APP_NAME} v{settings.VERSION}")
    logger.info(f"📅 {datetime.now().isoformat()}")
    logger.info(f"🌐 Ambiente: {settings.ENVIRONMENT}")
    logger.info(f"🗄️  Database: {'✓ Configurado' if settings.DATABASE_URL else '✗ No configurado'}")
    logger.info(f"📝 Docs: /docs")
    logger.info(f"💚 Health: /health")
    logger.info("=" * 50)

@app.on_event("shutdown")
async def shutdown_event():
    """Evento de cierre"""
    logger.info("👋 Cerrando aplicación...")

@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }
