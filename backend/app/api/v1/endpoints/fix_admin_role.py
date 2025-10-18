# backend/app/api/v1/endpoints/fix_admin_role.py
"""
Endpoint temporal para cambiar rol de usuario a ADMIN
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.api.deps import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/fix-admin-role")
def fix_admin_role(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🔧 Endpoint temporal para cambiar rol de usuario a ADMIN
    Solo para itmaster@rapicreditca.com
    """
    try:
        # Verificar que sea el usuario correcto
        if current_user.email != "itmaster@rapicreditca.com":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo itmaster@rapicreditca.com puede usar este endpoint"
            )
        
        # Buscar el usuario
        usuario = db.query(User).filter(User.email == "itmaster@rapicreditca.com").first()
        
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        # Cambiar a administrador
        usuario.is_admin = True
        db.commit()
        
        logger.info(f"✅ Usuario marcado como administrador para {usuario.email}")
        
        return {
            "status": "success",
            "message": "Usuario marcado como administrador exitosamente",
            "user": {
                "id": usuario.id,
                "email": usuario.email,
                "nombre": usuario.nombre,
                "apellido": usuario.apellido,
                "is_admin": usuario.is_admin,
                "is_active": usuario.is_active
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error marcando como administrador: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error marcando como administrador: {str(e)}"
        )
