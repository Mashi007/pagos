"""
Endpoint de health check mejorado
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint que verifica:
    - API está funcionando
    - Base de datos es accesible
    """
    try:
        # Verificar conexión a la base de datos
        db.execute(text("SELECT 1"))
        
        return {
            "status": "healthy",
            "service": "Sistema de Préstamos y Cobranza",
            "version": "1.0.0",
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "service": "Sistema de Préstamos y Cobranza",
            "version": "1.0.0",
            "database": "disconnected",
            "error": str(e)
        }


@router.get("/", status_code=status.HTTP_200_OK)
async def root():
    """
    Root endpoint
    """
    return {
        "message": "Sistema de Préstamos y Cobranza API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }
