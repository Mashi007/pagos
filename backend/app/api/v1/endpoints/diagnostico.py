# backend/app/api/v1/endpoints/diagnostico.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from app.db.session import get_db, SessionLocal
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
def health_check():
    """Verificación básica de salud del servicio"""
    return {
        "status": "healthy",
        "service": "backend",
        "version": "1.0.0"
    }


@router.get("/database")
def database_check(db: Session = Depends(get_db)):
    """Verificación de conexión a la base de datos"""
    try:
        # Prueba simple de conexión
        result = db.execute(text("SELECT 1 as test")).fetchone()
        return {
            "status": "connected",
            "database": "postgresql",
            "test_query": result[0] if result else None
        }
    except Exception as e:
        logger.error(f"Error en verificación de base de datos: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Error de conexión a base de datos: {str(e)}"
        )


@router.get("/database/direct")
def database_direct_check():
    """Verificación directa de conexión a la base de datos (sin dependency)"""
    try:
        db = SessionLocal()
        result = db.execute(text("SELECT 1 as test")).fetchone()
        db.close()
        return {
            "status": "connected",
            "method": "direct_connection",
            "test_query": result[0] if result else None
        }
    except Exception as e:
        logger.error(f"Error en verificación directa de base de datos: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Error de conexión directa a base de datos: {str(e)}"
        )


@router.get("/auth/test")
def auth_test(current_user: User = Depends(get_current_user)):
    """Verificación de autenticación"""
    return {
        "status": "authenticated",
        "user_id": current_user.id,
        "user_email": current_user.email,
        "user_role": current_user.rol
    }


@router.get("/clientes/test")
def clientes_test(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Verificación específica del endpoint de clientes"""
    try:
        from app.models.cliente import Cliente
        
        # Prueba simple de query de clientes
        count = db.query(Cliente).count()
        
        return {
            "status": "success",
            "user_authenticated": True,
            "user_id": current_user.id,
            "user_role": current_user.rol,
            "cliente_count": count,
            "database_connection": "ok"
        }
    except Exception as e:
        logger.error(f"Error en test de clientes: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Error en endpoint de clientes: {str(e)}"
        )
