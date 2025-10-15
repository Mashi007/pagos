"""
Endpoint de emergencia para corregir usuario administrador
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.core.security import get_password_hash
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/fix-admin-user")
def fix_admin_user(db: Session = Depends(get_db)):
    """
    🔧 EMERGENCY FIX: Corregir usuario administrador
    """
    try:
        logger.info("🔧 Iniciando corrección de usuario administrador...")
        
        # Buscar usuarios admin existentes
        admins = db.query(User).filter(User.rol == "ADMINISTRADOR_GENERAL").all()
        
        if not admins:
            raise HTTPException(status_code=404, detail="No se encontraron usuarios administradores")
        
        logger.info(f"📋 Encontrados {len(admins)} usuarios administradores")
        
        # Buscar el usuario correcto
        correct_admin = db.query(User).filter(User.email == "itmaster@rapicreditca.com").first()
        
        if correct_admin:
            logger.info("✅ Usuario itmaster@rapicreditca.com ya existe y está activo")
            return {
                "message": "Usuario itmaster@rapicreditca.com ya existe",
                "email": correct_admin.email,
                "active": correct_admin.is_active,
                "role": correct_admin.rol,
                "status": "ok"
            }
        
        # Actualizar admin@financiamiento.com a itmaster@rapicreditca.com
        old_admin = db.query(User).filter(User.email == "admin@financiamiento.com").first()
        
        if old_admin:
            logger.info("🔄 Actualizando admin@financiamiento.com a itmaster@rapicreditca.com...")
            
            old_admin.email = "itmaster@rapicreditca.com"
            old_admin.nombre = "IT Master"
            old_admin.apellido = "Sistema"
            old_admin.hashed_password = get_password_hash("R@pi_2025**")
            old_admin.rol = "ADMINISTRADOR_GENERAL"
            old_admin.is_active = True
            old_admin.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(old_admin)
            
            logger.info("✅ Usuario actualizado exitosamente")
            
            return {
                "message": "Usuario administrador actualizado exitosamente",
                "email": old_admin.email,
                "password": "R@pi_2025**",
                "role": old_admin.rol,
                "active": old_admin.is_active,
                "status": "updated"
            }
        else:
            # Crear nuevo usuario si no existe ninguno
            logger.info("📝 Creando nuevo usuario itmaster@rapicreditca.com...")
            
            new_admin = User(
                email="itmaster@rapicreditca.com",
                nombre="IT Master",
                apellido="Sistema",
                hashed_password=get_password_hash("R@pi_2025**"),
                rol="ADMINISTRADOR_GENERAL",
                is_active=True,
                created_at=datetime.utcnow()
            )
            
            db.add(new_admin)
            db.commit()
            db.refresh(new_admin)
            
            logger.info("✅ Usuario creado exitosamente")
            
            return {
                "message": "Usuario administrador creado exitosamente",
                "email": new_admin.email,
                "password": "R@pi_2025**",
                "role": new_admin.rol,
                "active": new_admin.is_active,
                "status": "created"
            }
            
    except Exception as e:
        logger.error(f"❌ Error corrigiendo usuario admin: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.get("/check-admin-users")
def check_admin_users(db: Session = Depends(get_db)):
    """
    🔍 Verificar usuarios administradores existentes
    """
    try:
        admins = db.query(User).filter(User.rol == "ADMINISTRADOR_GENERAL").all()
        
        result = []
        for admin in admins:
            result.append({
                "id": admin.id,
                "email": admin.email,
                "nombre": admin.nombre,
                "apellido": admin.apellido,
                "rol": admin.rol,
                "is_active": admin.is_active,
                "created_at": admin.created_at.isoformat() if admin.created_at else None
            })
        
        return {
            "message": f"Encontrados {len(admins)} usuarios administradores",
            "admins": result,
            "total": len(admins)
        }
        
    except Exception as e:
        logger.error(f"❌ Error verificando usuarios admin: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
