"""
Aplicación principal FastAPI
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import api_router
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Crear aplicación FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    expose_headers=["X-Total-Count", "X-Page-Count"],
    max_age=3600,
)

# Incluir routers
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.on_event("startup")
def on_startup():
    """Crear tablas en la BD si no existen. Inicializar config de email desde .env."""
    from sqlalchemy import text
    from app.core.database import engine
    from app.models import Base, Cliente, Ticket, Cuota  # noqa: F401 - registran tablas en Base.metadata
    from app.core.email_config_holder import init_from_settings as init_email_config

    init_email_config()
    logger.info("Configuración de email (SMTP/tickets) inicializada desde variables de entorno.")

    # Crear todas las tablas (incluye clientes) si no existen
    Base.metadata.create_all(bind=engine)
    logger.info("Base de datos: tablas creadas o ya existentes.")

    # Verificar que la tabla clientes existe y está accesible
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM clientes LIMIT 1"))
        logger.info("Tabla clientes: conectada y accesible.")
    except Exception as e:
        logger.warning("Tabla clientes: verificación fallida (puede ser tabla vacía o recién creada): %s", e)


@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "message": f"Bienvenido a {settings.PROJECT_NAME}",
        "version": settings.VERSION,
        "docs": "/docs"
    }


@app.head("/")
async def root_head():
    """Endpoint raíz para HEAD requests (health checks)"""
    return


@app.get("/health")
async def health_check():
    """Endpoint de salud"""
    return {"status": "healthy"}


@app.get("/health/db")
async def health_check_db():
    """Verifica que la conexión a la BD responde (SELECT 1)."""
    from sqlalchemy import text
    from fastapi.responses import JSONResponse
    from app.core.database import engine
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.exception("Health check DB failed")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "disconnected", "error": str(e)},
        )


@app.head("/health")
async def health_check_head():
    """Endpoint de salud para HEAD requests"""
    return


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
