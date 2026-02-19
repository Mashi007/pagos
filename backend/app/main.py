"""
Aplicación principal FastAPI
"""
import time
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings
from app.api.v1 import api_router

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class RequestLogMiddleware(BaseHTTPMiddleware):
    """Registra método, ruta, código de estado y tiempo para correlacionar con logs de Render."""
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            "request method=%s path=%s status=%s elapsed_ms=%s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response


# Crear aplicación FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Log de cada request (método, ruta, status, tiempo) para depuración en Render
app.add_middleware(RequestLogMiddleware)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    expose_headers=["X-Total-Count", "X-Page-Count"],
    max_age=3600,
)

# Incluir routers
app.include_router(api_router, prefix=settings.API_V1_STR)


def _startup_db_with_retry(engine, max_attempts: int = 5, delay_sec: float = 2.0):
    """Intenta crear tablas y verificar BD con reintentos (evita fallo por BD no lista en Render)."""
    from sqlalchemy import text
    from app.models import (  # noqa: F401
        Base, Cliente, Prestamo, Ticket, Cuota, PagosWhatsapp, Configuracion, Auditoria,
        User, DefinicionCampo, ConversacionAI, DiccionarioSemantico,
        ConversacionCobranza, MensajeWhatsapp, PagosInforme,
        PlantillaNotificacion, VariableNotificacion,
    )
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Base de datos: tablas creadas o ya existentes.")
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Conexión a BD verificada.")
            return
        except Exception as e:
            last_error = e
            logger.warning(
                "Intento %s/%s de conexión a BD falló: %s. Reintentando en %.1fs...",
                attempt, max_attempts, e, delay_sec,
            )
            if attempt < max_attempts:
                time.sleep(delay_sec)
    logger.error("No se pudo conectar a la BD tras %s intentos: %s", max_attempts, last_error)
    raise last_error


@app.on_event("startup")
def on_startup():
    """Crear tablas en la BD si no existen. Inicializar config de email desde .env. Iniciar scheduler de reportes cobranzas."""
    from app.core.database import engine
    from app.core.email_config_holder import init_from_settings as init_email_config
    from app.core.scheduler import start_scheduler

    init_email_config()
    logger.info("Configuración de email (SMTP/tickets) inicializada desde variables de entorno.")

    # Crear tablas y verificar BD con reintentos (Render puede tener la BD aún no lista en el primer worker)
    try:
        _startup_db_with_retry(engine)
    except Exception as e:
        logger.exception("Startup BD falló tras reintentos: %s", e)
        raise

    # Scheduler: reportes de cobranzas a las 6:00 y 13:00 (America/Caracas)
    try:
        start_scheduler()
    except Exception as e:
        logger.exception("No se pudo iniciar el scheduler de reportes cobranzas: %s", e)

    # Caché dashboard: actualización a las 1:00 y 13:00 (hora local) para cargas rápidas
    try:
        from app.api.v1.endpoints.dashboard import start_dashboard_cache_refresh
        start_dashboard_cache_refresh()
    except Exception as e:
        logger.exception("No se pudo iniciar el worker de caché dashboard: %s", e)


@app.on_event("shutdown")
def on_shutdown():
    """Detener scheduler al cerrar la aplicación."""
    try:
        from app.core.scheduler import stop_scheduler
        stop_scheduler()
    except Exception as e:
        logger.warning("Al detener scheduler: %s", e)


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


@app.post("/api/admin/run-migration-auditoria-fk")
async def run_migration_auditoria_fk(request: Request):
    """
    Ejecuta la migración auditoria.usuario_id FK -> usuarios(id).
    Requiere header: X-Migration-Secret = MIGRATION_AUDITORIA_SECRET (env).
    Ejecutar una sola vez para corregir el error 500 en aprobación manual.
    """
    from fastapi import HTTPException
    from sqlalchemy import text
    from app.core.database import engine

    secret = settings.MIGRATION_AUDITORIA_SECRET
    if not secret:
        raise HTTPException(status_code=404, detail="Endpoint no configurado")
    header_secret = request.headers.get("X-Migration-Secret")
    if header_secret != secret:
        raise HTTPException(status_code=403, detail="Secreto inválido")

    try:
        with engine.connect() as conn:
            with conn.begin():
                conn.execute(text("""
                    ALTER TABLE auditoria DROP CONSTRAINT IF EXISTS auditoria_usuario_id_fkey
                """))
                conn.execute(text("""
                    ALTER TABLE auditoria ADD CONSTRAINT auditoria_usuario_id_fkey
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) NOT VALID
                """))
        return {"success": True, "message": "Migración auditoria FK completada. La aprobación manual debería funcionar."}
    except Exception as e:
        logger.exception("Migración auditoria FK falló: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


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
