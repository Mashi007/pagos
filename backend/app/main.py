"""
Aplicación principal FastAPI
"""
import time
import logging
import warnings
from datetime import datetime

# Evitar ruido en logs por versiones de urllib3/chardet (dependencias de requests)
warnings.filterwarnings("ignore", message=".*urllib3.*chardet.*", category=UserWarning, module="requests")

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.api.v1 import api_router
from app.middleware.audit_middleware import AuditMiddleware
from app.middleware.validador_sobre_aplicacion import ValidadorSobreAplicacionMiddleware
from app.services.liquidado_scheduler import liquidado_scheduler

# Configurar logging con UTF-8 para tildes/caracteres en Render
import sys
import io
_log_stream = io.TextIOWrapper(getattr(sys.stderr, "buffer", sys.stderr), encoding="utf-8", errors="replace")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=_log_stream,
    force=True,
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

def _cors_headers_for_request(request: Request):
    """Cabeceras CORS para respuestas de error (500, etc.) que el navegador pueda leer."""
    origin = request.headers.get("origin")
    allowed = settings.cors_origins_list
    if origin and origin in allowed:
        return {"Access-Control-Allow-Origin": origin}
    if allowed:
        return {"Access-Control-Allow-Origin": allowed[0]}
    return {}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Respuesta de error unificada: detail + code para el frontend. Incluye CORS para evitar bloqueo en 4xx/5xx."""
    from app.core.exceptions import error_response_body
    headers = _cors_headers_for_request(request)
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response_body(exc.detail, exc.status_code),
        headers=headers,
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Captura excepciones no controladas y devuelve 500 con CORS para que el frontend reciba el error."""
    logger.exception("Excepcion no controlada: %s", exc)
    headers = _cors_headers_for_request(request)
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor", "code": 500},
        headers=headers,
    )


# Log de cada request (método, ruta, status, tiempo) para depuración en Render
app.add_middleware(RequestLogMiddleware)

# Middleware: Validaci�n en tiempo real de sobre-aplicaciones
app.add_middleware(ValidadorSobreAplicacionMiddleware)

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

# Incluir endpoint del scheduler de LIQUIDADO
from app.api.v1.endpoints import prestamos_liquidado_automatico
app.include_router(prestamos_liquidado_automatico.router)
# Incluir endpoint de conciliaci�n autom�tica
from app.api.v1.endpoints import conciliacion
app.include_router(conciliacion.router)
# Incluir endpoint de referencia de estados de cuota
from app.api.v1.endpoints import referencia_estados_cuota
app.include_router(referencia_estados_cuota.router)
# Incluir endpoint de auditor�a de conciliaci�n
from app.api.v1.endpoints import auditoria_conciliacion
app.include_router(auditoria_conciliacion.router)
# Incluir endpoint de problemas cr�ticos (diagn�stico y correcci�n)
from app.api.v1.endpoints import criticos
app.include_router(criticos.router)
# Incluir dashboard de monitoreo
from app.api.v1.endpoints import dashboard_conciliacion
app.include_router(dashboard_conciliacion.router)


def _startup_db_with_retry(engine, max_attempts: int = 10, delay_sec: float = 3.0):
    """Intenta crear tablas y verificar BD con reintentos (evita fallo por BD no lista en Render).
    
    Mejorado:
    - Aumentados intentos de 5 a 10
    - Delay inicial de 3 segundos con backoff exponencial
    - Verificación explícita de que la tabla 'prestamos' existe
    - Logging más detallado para debugging en Render
    """
    from sqlalchemy import text, inspect
    # Importar todos los modelos para que Base.metadata tenga todas las tablas (pagos_reportados, usuarios, etc.)
    import app.models as _  # noqa: F401
    from app.models import Base
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

    # Scheduler: solo un worker (leader) inicia los jobs para evitar duplicados con --workers 2
    try:
        from app.core.database import SessionLocal
        from app.core.scheduler_leader import try_claim_scheduler_leader, start_scheduler_leader_heartbeat
        db = SessionLocal()
        try:
            if try_claim_scheduler_leader(db):
                start_scheduler()
                start_scheduler_leader_heartbeat()
                app.state._scheduler_leader = True
            else:
                app.state._scheduler_leader = False
        finally:
            db.close()
    except Exception as e:
        logger.exception("No se pudo iniciar el scheduler de reportes cobranzas: %s", e)

    # Caché dashboard: actualización a las 1:00 y 13:00 (hora local) para cargas rápidas
    try:
        from app.api.v1.endpoints.dashboard import start_dashboard_cache_refresh
        start_dashboard_cache_refresh()
    except Exception as e:
        logger.exception("No se pudo iniciar el worker de caché dashboard: %s", e)

# Scheduler automatico de LIQUIDADO: ejecutar a las 21:00 (9 PM) diariamente
    try:
        liquidado_scheduler.iniciar_scheduler()
        logger.info('Scheduler de actualizacion a LIQUIDADO iniciado (9 PM diariamente)')
    except Exception as e:
        logger.warning('No se pudo iniciar el scheduler de LIQUIDADO: %s', e)

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
    """Detener scheduler y heartbeat de leader al cerrar la aplicación."""
    # Detener scheduler de LIQUIDADO
    try:
        liquidado_scheduler.detener_scheduler()
        logger.info('Scheduler de LIQUIDADO detenido')
    except Exception as e:
        logger.warning('Error al detener scheduler de LIQUIDADO: %s', e)
    
    try:
        if getattr(app.state, "_scheduler_leader", False):
            from app.core.scheduler_leader import stop_scheduler_leader_heartbeat
            stop_scheduler_leader_heartbeat()
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






