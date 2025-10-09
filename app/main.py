# app/main.py
from fastapi import FastAPI, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

# Configuración
from app.config import settings

# Base de datos
from app.db.init_db import init_database
from app.db.session import get_db

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

# Health check endpoint
@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Endpoint de health check para Railway"""
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
    """Endpoint raíz con información de la API"""
    return {
        "message": "API Sistema de Pagos y Cobranza",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "endpoints": {
            "clientes": "/api/v1/clientes",
            "pagos": "/api/v1/pagos",
            "database": "/test/database",
            "init_db": "/test/init-db"
        }
    }

# ========================================
# ENDPOINTS DE PRUEBA DE BASE DE DATOS
# ========================================

@app.get("/test/database", status_code=status.HTTP_200_OK)
async def test_database(db: Session = Depends(get_db)):
    """Probar conexión a la base de datos"""
    try:
        # Probar consulta simple
        db.execute(text("SELECT 1"))
        
        # Verificar tablas
        result_tables = db.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """))
        tables = [row[0] for row in result_tables]
        
        return {
            "status": "ok",
            "message": "✅ Conexión a base de datos exitosa",
            "database_connected": True,
            "tables": tables,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "message": f"❌ Error conectando a BD: {str(e)}",
                "database_connected": False,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@app.post("/test/init-db", status_code=status.HTTP_200_OK)
async def initialize_database():
    """Inicializar las tablas de la base de datos"""
    try:
        init_database()
        return {
            "status": "ok",
            "message": "✅ Tablas creadas correctamente",
            "tables": ["clientes", "pagos"],
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "message": f"❌ Error inicializando BD: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
        )

# Manejo de errores global
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Manejador global de excepciones"""
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
    """Tareas al iniciar la aplicación"""
    print("=" * 50)
    print(f"🚀 Servidor FastAPI iniciado")
    print(f"📅 Timestamp: {datetime.utcnow().isoformat()}")
    print(f"🌐 Ambiente: {settings.ENVIRONMENT}")
    print(f"🗄️  Database: {'✓ Configurado' if settings.DATABASE_URL else '✗ NO configurado'}")
    print(f"📝 Docs: /docs")
    print(f"💚 Health: /health")
    print("=" * 50)

# Evento de cierre
@app.on_event("shutdown")
async def shutdown_event():
    """Tareas al cerrar la aplicación"""
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
