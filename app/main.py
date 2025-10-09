from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from datetime import datetime

# Configuración
from app.config import settings

# Importar routers cuando estén creados
# from app.api.v1 import auth, users, clientes, pagos

app = FastAPI(
    title="Sistema de Pagos y Cobranza",
    description="API para gestión de préstamos, pagos y cobranza",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configuración CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint (requerido por Railway)
@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Endpoint de health check para Railway y monitoreo
    """
    return {
        "status": "ok",
        "service": "Sistema de Pagos",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.ENVIRONMENT,
        "version": "1.0.0"
    }

# Endpoint raíz
@app.get("/", status_code=status.HTTP_200_OK)
async def root():
    """
    Endpoint raíz con información de la API
    """
    return {
        "message": "API Sistema de Pagos y Cobranza",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "api_v1": "/api/v1",
        "endpoints": {
            "auth": "/api/v1/auth",
            "users": "/api/v1/users",
            "clientes": "/api/v1/clientes",
            "pagos": "/api/v1/pagos",
            "reportes": "/api/v1/reportes",
            "kpis": "/api/v1/kpis"
        }
    }

# Ruta API v1
@app.get("/api/v1", status_code=status.HTTP_200_OK)
async def api_v1_root():
    """
    Información de la API v1
    """
    return {
        "message": "API v1 funcionando correctamente",
        "timestamp": datetime.utcnow().isoformat(),
        "available_endpoints": [
            "/api/v1/auth",
            "/api/v1/users",
            "/api/v1/clientes",
            "/api/v1/pagos",
            "/api/v1/amortizacion",
            "/api/v1/conciliacion",
            "/api/v1/reportes",
            "/api/v1/kpis",
            "/api/v1/notificaciones",
            "/api/v1/aprobaciones",
            "/api/v1/configuracion"
        ]
    }

# Incluir routers (descomentar cuando estén creados)
# app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
# app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
# app.include_router(clientes.router, prefix="/api/v1/clientes", tags=["clientes"])
# app.include_router(pagos.router, prefix="/api/v1/pagos", tags=["pagos"])

# Manejo de errores global
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Manejador global de excepciones
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Error interno del servidor",
            "message": str(exc) if settings.ENVIRONMENT == "development" else "Error procesando la solicitud",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# Evento de inicio
@app.on_event("startup")
async def startup_event():
    """
    Tareas al iniciar la aplicación
    """
    print("=" * 50)
    print(f"🚀 Servidor FastAPI iniciado")
    print(f"📅 Timestamp: {datetime.utcnow().isoformat()}")
    print(f"🌐 Ambiente: {settings.ENVIRONMENT}")
    print(f"🗄️  Database: {'Configurado' if settings.DATABASE_URL else 'NO configurado'}")
    print(f"📝 Docs: /docs")
    print("=" * 50)

# Evento de cierre
@app.on_event("shutdown")
async def shutdown_event():
    """
    Tareas al cerrar la aplicación
    """
    print("🛑 Servidor FastAPI detenido")

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.ENVIRONMENT == "development"
    )
