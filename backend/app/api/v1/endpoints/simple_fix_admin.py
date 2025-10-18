# backend/app/api/v1/endpoints/simple_fix_admin.py
"""
Endpoint simple para cambiar rol de usuario a ADMIN
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/change-to-admin")
def change_to_admin(
    db: Session = Depends(get_db)
):
    """
    🔧 Endpoint simple para cambiar rol de usuario a ADMIN
    Solo para itmaster@rapicreditca.com
    """
    try:
        # Buscar el usuario
        usuario = db.query(User).filter(User.email == "itmaster@rapicreditca.com").first()
        
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        # Cambiar rol a ADMIN
        usuario.rol = "ADMIN"
        db.commit()
        
        logger.info(f"✅ Rol cambiado a ADMIN para {usuario.email}")
        
        return {
            "status": "success",
            "message": "Rol cambiado a ADMIN exitosamente",
            "user": {
                "id": usuario.id,
                "email": usuario.email,
                "nombre": usuario.nombre,
                "apellido": usuario.apellido,
                "rol": usuario.rol,
                "is_active": usuario.is_active
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error cambiando rol: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error cambiando rol: {str(e)}"
        )
