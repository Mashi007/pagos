# app/api/v1/endpoints/health.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.init_db import check_database_connection
from app.config import get_settings  # ✅ CAMBIO: importar función factory
from datetime import datetime

router = APIRouter()

@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    
    settings = get_settings()  # ✅ CAMBIO: obtener settings aquí
    db_status = check_database_connection()
    
    return {
        "status": "healthy" if db_status else "unhealthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,  # ✅ CORRECCIÓN: era settings.VERSION
        "environment": settings.ENVIRONMENT,
        "database": "connected" if db_status else "disconnected",
        "timestamp": datetime.utcnow().isoformat()
    }

@router.post("/test/init-db")
async def initialize_database():
    """Endpoint para inicializar la base de datos"""
    from app.db.init_db import init_database
    
    try:
        success = init_database()
        if success:
            return {"status": "success", "message": "✅ Base de datos inicializada"}
        else:
            return {"status": "error", "message": "❌ Error inicializando base de datos"}
    except Exception as e:
        return {"status": "error", "message": f"❌ Error: {str(e)}"}
