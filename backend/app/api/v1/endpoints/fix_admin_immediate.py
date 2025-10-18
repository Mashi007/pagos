# backend/app/api/v1/endpoints/fix_admin_immediate.py
"""
Endpoint temporal para corregir el estado de administrador del usuario itmaster@rapicreditca.com
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.session import get_db
from app.models.user import User

router = APIRouter()

@router.post("/fix-admin-immediate")
def fix_admin_immediate(db: Session = Depends(get_db)):
    """
    CORRECCIÓN INMEDIATA: Marcar itmaster@rapicreditca.com como administrador
    """
    try:
        # Verificar estado actual
        result = db.execute(text("""
            SELECT id, email, nombre, apellido, is_admin, is_active 
            FROM usuarios 
            WHERE email = 'itmaster@rapicreditca.com'
        """)).fetchone()
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario itmaster@rapicreditca.com no encontrado"
            )
        
        user_id, email, nombre, apellido, is_admin, is_active = result
        
        if is_admin:
            return {
                "status": "success",
                "message": "El usuario ya es administrador",
                "user": {
                    "id": user_id,
                    "email": email,
                    "nombre": nombre,
                    "apellido": apellido,
                    "is_admin": is_admin,
                    "is_active": is_active
                }
            }
        
        # Corregir el estado
        db.execute(text("""
            UPDATE usuarios 
            SET is_admin = TRUE, updated_at = NOW()
            WHERE email = 'itmaster@rapicreditca.com'
        """))
        db.commit()
        
        # Verificar el cambio
        result = db.execute(text("""
            SELECT is_admin 
            FROM usuarios 
            WHERE email = 'itmaster@rapicreditca.com'
        """)).fetchone()
        
        if result and result[0]:
            return {
                "status": "success",
                "message": "Usuario marcado como administrador exitosamente",
                "user": {
                    "id": user_id,
                    "email": email,
                    "nombre": nombre,
                    "apellido": apellido,
                    "is_admin": True,
                    "is_active": is_active
                }
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al marcar usuario como administrador"
            )
            
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error durante la corrección: {str(e)}"
        )
