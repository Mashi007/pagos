"""
Aplicación principal FastAPI
"""
import time
import logging
import warnings
from datetime import datetime

# Evitar ruido en logs por versiones de urllib3/chardet (dependencias de requests)
warnings.filterwarnings("ignore", message=".*urllib3.*chardet.*", category=UserWarning, module="requests")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings
from app.api.v1 import api_router
from app.middleware.audit_middleware import AuditMiddleware

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
        status = response.status_code
        path = request.url.path
        msg = "request method=%s path=%s status=%s elapsed_ms=%s"
        # run-now puede tardar 20–120 s; no marcar como slow
        is_run_now = "gmail/run-now" in path
        if status >= 500:
            logger.warning(msg + " (error)", request.method, path, status, elapsed_ms)
        elif not is_run_now and elapsed_ms >= 5000:
            logger.warning(msg + " (slow)", request.method, path, status, elapsed_ms)
        elif request.method == "POST" and path.rstrip("/").endswith("/api/v1/pagos") and status == 409:
            # 409 documento duplicado en carga masiva: muchos por lote; solo DEBUG para no saturar logs
            logger.debug(msg, request.method, path, status, elapsed_ms)
        else:
            logger.info(msg, request.method, path, status, elapsed_ms)
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

# Auditoría automática: registra todos los POST/PUT/DELETE/PATCH en tabla auditoria
app.add_middleware(AuditMiddleware)

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


def _startup_db_with_retry(engine, max_attempts: int = 10, delay_sec: float = 3.0):
    """Intenta crear tablas y verificar BD con reintentos (evita fallo por BD no lista en Render).
    
    Mejorado:
    - Aumentados intentos de 5 a 10
    - Delay inicial de 3 segundos con backoff exponencial
    - Verificación explícita de que la tabla 'prestamos' existe
    - Logging más detallado para debugging en Render
    """
    from sqlalchemy import text, inspect
    from app.models import (  # noqa: F401
        Base, Cliente, Prestamo, Ticket, Cuota, PagosWhatsapp, Configuracion, Auditoria,
        User, DefinicionCampo, ConversacionAI, DiccionarioSemantico,
        ConversacionCobranza, MensajeWhatsapp, PagosInforme,
        PlantillaNotificacion, VariableNotificacion,
    )
    last_error = None
    current_delay = delay_sec
    
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"[DB Startup {attempt}/{max_attempts}] Conectando a base de datos...")
            
            # Crear tablas
            Base.metadata.create_all(bind=engine)
            logger.info("[DB Startup] Tablas creadas o ya existentes.")
            
            # Verificar conexión básica
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                if not result.fetchone():
                    raise Exception("SELECT 1 no retornó resultado")
            logger.info("[DB Startup] Conexión básica verificada.")
            
            # Verificar que tabla crítica 'prestamos' existe
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            logger.info(f"[DB Startup] Tablas en BD: {tables}")
            
            if 'prestamos' not in tables:
                raise Exception("Tabla crítica 'prestamos' no fue creada. Tablas disponibles: " + str(tables))
            
            logger.info("[DB Startup] ✅ Tabla 'prestamos' verificada exitosamente.")
            
            # Contar registros en tabla crítica para verificar acceso
            with engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM prestamos"))
                count = result.scalar()
                logger.info(f"[DB Startup] Tabla 'prestamos' contiene {count} registros.")

            logger.info("[DB Startup] ✅ BASE DE DATOS INICIALIZADA CORRECTAMENTE")

            # Migración en caliente: columna drive_email_link (link al .eml en Drive) si no existe
            try:
                with engine.connect() as conn:
                    r = conn.execute(text("""
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'pagos_gmail_sync_item' AND column_name = 'drive_email_link'
                    """))
                    if r.fetchone() is None:
                        conn.execute(text(
                            "ALTER TABLE pagos_gmail_sync_item ADD COLUMN drive_email_link VARCHAR(500) NULL"
                        ))
                        conn.commit()
                        logger.info("[DB Startup] Columna pagos_gmail_sync_item.drive_email_link añadida.")
            except Exception as col_err:
                logger.warning("[DB Startup] drive_email_link (no crítico): %s", col_err)

            return

        except Exception as e:
            last_error = e
            logger.warning(
                f"[DB Startup {attempt}/{max_attempts}] Error: {type(e).__name__}: {str(e)[:200]}"
            )
            
            if attempt < max_attempts:
                logger.info(f"[DB Startup] Reintentando en {current_delay:.1f}s...")
                time.sleep(current_delay)
                current_delay *= 1.5  # Backoff exponencial: 3s, 4.5s, 6.75s, etc.
    
    logger.error(
        f"[DB Startup] ❌ FALLO CRÍTICO tras {max_attempts} intentos. "
        f"Última excepción: {type(last_error).__name__}: {str(last_error)}"
    )
    raise RuntimeError(
        f"No se pudo inicializar la base de datos tras {max_attempts} intentos. "
        f"Error final: {str(last_error)}"
    ) from last_error


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

    # Limpiar syncs de Gmail que quedaron en estado "running" tras un reinicio inesperado (SIGTERM/deploy).
    # Si no se limpian, _is_pipeline_running bloquea nuevas ejecuciones.
    try:
        from app.core.database import SessionLocal
        from app.models.pagos_gmail_sync import PagosGmailSync
        from sqlalchemy import update as sa_update
        db_startup = SessionLocal()
        try:
            result = db_startup.execute(
                sa_update(PagosGmailSync)
                .where(PagosGmailSync.status == "running")
                .values(
                    status="error",
                    finished_at=datetime.utcnow(),
                    error_message="Reinicio del servidor (SIGTERM) mientras el pipeline estaba en curso.",
                )
            )
            if result.rowcount:
                logger.warning(
                    "[PAGOS_GMAIL] %d sync(s) en estado 'running' marcadas como 'error' al reiniciar (SIGTERM durante despliegue).",
                    result.rowcount,
                )
            db_startup.commit()
        finally:
            db_startup.close()
    except Exception as e:
        logger.warning("[PAGOS_GMAIL] No se pudieron limpiar syncs huérfanas al iniciar: %s", e)


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


@app.get("/health/gemini")
async def health_check_gemini_root():
    """Test indirecto de Gemini (API key y servicio). Disponible también en GET /api/v1/health/gemini."""
    from fastapi import HTTPException
    from app.services.pagos_gmail.gemini_service import check_gemini_available
    result = check_gemini_available()
    if not result.get("ok"):
        raise HTTPException(status_code=503, detail=result)
    return result


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
