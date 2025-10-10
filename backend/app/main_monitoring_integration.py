# backend/app/main_monitoring_integration.py
"""
EJEMPLO: Cómo integrar el monitoreo en tu main.py existente
"""

# ==========================================
# AGREGAR ESTOS IMPORTS
# ==========================================
from app.core.monitoring import setup_monitoring

# ==========================================
# EN TU FUNCIÓN create_app() O INICIO
# ==========================================
def create_app() -> FastAPI:
    app = FastAPI(
        title="Sistema de Préstamos y Cobranza",
        version="1.0.0"
    )
    
    # ... tu configuración existente ...
    
    # ✅ AGREGAR ESTO: Configurar monitoreo
    monitoring_config = setup_monitoring(app)
    
    # Logging de configuración
    if monitoring_config.get("sentry"):
        logger.info("✅ Sentry habilitado")
    
    if monitoring_config.get("prometheus"):
        logger.info("✅ Prometheus habilitado - Métricas en /metrics")
    
    # ... resto de tu código ...
    
    return app

# ==========================================
# EJEMPLO COMPLETO DE MAIN.PY
# ==========================================
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.config import settings
from app.core.monitoring import setup_monitoring
from app.db.session import engine
from app.db.init_db import init_db
from app.api.v1 import api_router

logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        openapi_url=f"{settings.API_V1_STR}/openapi.json"
    )
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # ✅ MONITOREO
    setup_monitoring(app)
    
    # Routers
    app.include_router(api_router, prefix=settings.API_V1_STR)
    
    return app

app = create_app()

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Iniciando aplicación...")
    init_db()
    logger.info("✅ Base de datos inicializada")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 Cerrando aplicación...")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }
"""

# ==========================================
# ENDPOINTS DE MONITOREO AUTOMÁTICOS
# ==========================================
"""
Una vez configurado, tendrás:

GET /health         - Health check básico
GET /metrics        - Métricas de Prometheus
GET /docs          - Documentación Swagger

Métricas disponibles en /metrics:
- http_requests_total
- http_request_duration_seconds
- http_requests_inprogress
- process_cpu_seconds_total
- process_resident_memory_bytes
- Y más...
"""

# ==========================================
# USO EN ENDPOINTS
# ==========================================
"""
from app.core.monitoring import track_operation
from fastapi import APIRouter

router = APIRouter()

@router.post("/prestamos")
async def crear_prestamo(prestamo: PrestamoCreate, db: Session = Depends(get_db)):
    # Track la operación
    with track_operation("crear_prestamo", categoria=prestamo.categoria):
        # Tu lógica aquí
        nuevo_prestamo = ...
        db.add(nuevo_prestamo)
        db.commit()
        
    return nuevo_prestamo
"""

# ==========================================
# CAPTURA DE ERRORES CON SENTRY
# ==========================================
"""
# Los errores se capturan automáticamente, pero puedes capturar manualmente:

import sentry_sdk

try:
    # código que puede fallar
    resultado = operacion_riesgosa()
except Exception as e:
    sentry_sdk.capture_exception(e)
    # también puedes agregar contexto
    sentry_sdk.set_context("prestamo", {
        "id": prestamo_id,
        "monto": monto
    })
    raise
"""
