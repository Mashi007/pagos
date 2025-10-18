# backend/app/api/v1/endpoints/simple_debug.py
"""
Endpoint simple para debug del problema de refreshUser
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()

@router.get("/simple-user-info")
def simple_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Endpoint simple para obtener información del usuario
    """
    try:
        print(f"🔍 simple-user-info - Usuario: {current_user.email}, is_admin: {current_user.is_admin}")
        
        return {
            "status": "success",
            "user": {
                "id": current_user.id,
                "email": current_user.email,
                "nombre": current_user.nombre,
                "apellido": current_user.apellido,
                "is_admin": current_user.is_admin,
                "is_active": current_user.is_active,
                "cargo": current_user.cargo,
                "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
                "updated_at": current_user.updated_at.isoformat() if current_user.updated_at else None,
                "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        print(f"❌ simple-user-info - Error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.post("/simple-fix-admin")
def simple_fix_admin(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Endpoint simple para marcar usuario como admin
    """
    try:
        print(f"🔧 simple-fix-admin - Usuario: {current_user.email}, is_admin actual: {current_user.is_admin}")
        
        # Marcar como admin
        current_user.is_admin = True
        db.commit()
        db.refresh(current_user)
        
        print(f"✅ simple-fix-admin - Usuario marcado como admin: {current_user.is_admin}")
        
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
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        print(f"❌ simple-fix-admin - Error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
