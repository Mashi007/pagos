# backend/app/api/v1/endpoints/fix_refresh_user.py
"""
Endpoint temporal para arreglar el problema de refreshUser
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/fix-user-admin")
def fix_user_admin(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Arreglar el problema del usuario administrador
    """
    try:
        # 1. Verificar usuario actual
        user_info = {
            "id": current_user.id,
            "email": current_user.email,
            "nombre": current_user.nombre,
            "apellido": current_user.apellido,
            "is_admin": current_user.is_admin,
            "is_active": current_user.is_active,
        }
        
        # 2. Si el usuario actual no es admin, marcarlo como admin
        if not current_user.is_admin:
            logger.info(f"Marcando usuario {current_user.email} como administrador...")
            db.execute(text("""
                UPDATE usuarios 
                SET is_admin = TRUE 
                WHERE id = :user_id
            """), {"user_id": current_user.id})
            db.commit()
            
            # Refrescar el objeto usuario
            db.refresh(current_user)
            
            return {
                "status": "success",
                "message": "Usuario marcado como administrador exitosamente",
                "user": {
                    "id": current_user.id,
                    "email": current_user.email,
                    "nombre": current_user.nombre,
                    "apellido": current_user.apellido,
                    "is_admin": current_user.is_admin,
                    "is_active": current_user.is_active,
                }
            }
        else:
            return {
                "status": "success",
                "message": "Usuario ya es administrador",
                "user": user_info
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "user": None
        }

@router.get("/verify-user-status")
def verify_user_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verificar el estado del usuario actual
    """
    try:
        # Verificar en base de datos directamente
        result = db.execute(text("""
            SELECT id, email, nombre, apellido, is_admin, is_active, created_at, updated_at, last_login
            FROM usuarios 
            WHERE id = :user_id
        """), {"user_id": current_user.id})
        
        db_user = result.fetchone()
        
        if db_user:
            return {
                "status": "success",
                "current_user": {
                    "id": current_user.id,
                    "email": current_user.email,
                    "nombre": current_user.nombre,
                    "apellido": current_user.apellido,
                    "is_admin": current_user.is_admin,
                    "is_active": current_user.is_active,
                },
                "database_user": {
                    "id": db_user[0],
                    "email": db_user[1],
                    "nombre": db_user[2],
                    "apellido": db_user[3],
                    "is_admin": db_user[4],
                    "is_active": db_user[5],
                    "created_at": db_user[6].isoformat() if db_user[6] else None,
                    "updated_at": db_user[7].isoformat() if db_user[7] else None,
                    "last_login": db_user[8].isoformat() if db_user[8] else None,
                },
                "match": current_user.is_admin == db_user[4] and current_user.is_active == db_user[5]
            }
        else:
            return {
                "status": "error",
                "error": "Usuario no encontrado en base de datos",
                "current_user": {
                    "id": current_user.id,
                    "email": current_user.email,
                    "is_admin": current_user.is_admin,
                    "is_active": current_user.is_active,
                }
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "current_user": None
        }

@router.post("/force-refresh-user")
def force_refresh_user(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Forzar la actualización del usuario desde la base de datos
    """
    try:
        # Actualizar last_login
        db.execute(text("""
            UPDATE usuarios 
            SET last_login = NOW() 
            WHERE id = :user_id
        """), {"user_id": current_user.id})
        db.commit()
        
        # Refrescar el objeto usuario
        db.refresh(current_user)
        
        return {
            "status": "success",
            "message": "Usuario refrescado exitosamente",
            "user": {
                "id": current_user.id,
                "email": current_user.email,
                "nombre": current_user.nombre,
                "apellido": current_user.apellido,
                "is_admin": current_user.is_admin,
                "is_active": current_user.is_active,
                "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "user": None
        }
