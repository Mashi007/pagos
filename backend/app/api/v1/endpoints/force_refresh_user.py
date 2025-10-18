# backend/app/api/v1/endpoints/force_refresh_user.py
"""
Endpoint para forzar actualización del usuario en frontend
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/force-refresh-user")
def force_refresh_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Forzar actualización del usuario en frontend
    """
    try:
        logger.info(f"Forzando refresh del usuario: {current_user.email}")
        
        # Obtener permisos actualizados
        permissions = AuthService.get_user_permissions(current_user)
        
        # Crear respuesta con datos actualizados
        user_data = {
            "id": current_user.id,
            "email": current_user.email,
            "nombre": current_user.nombre,
            "apellido": current_user.apellido,
            "is_admin": current_user.is_admin,
            "cargo": current_user.cargo,
            "is_active": current_user.is_active,
            "created_at": current_user.created_at,
            "updated_at": current_user.updated_at,
            "last_login": current_user.last_login,
            "permissions": permissions
        }
        
        logger.info(f"Usuario actualizado - is_admin: {current_user.is_admin}, permisos: {len(permissions)}")
        
        return {
            "status": "success",
            "message": "Usuario actualizado exitosamente",
            "user": user_data,
            "debug": {
                "is_admin": current_user.is_admin,
                "total_permissions": len(permissions),
                "timestamp": current_user.updated_at
            }
        }
        
    except Exception as e:
        logger.error(f"Error forzando refresh del usuario: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error actualizando usuario: {str(e)}"
        )
