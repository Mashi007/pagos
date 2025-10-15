"""
Endpoint específico para eliminar admin@financiamiento.com
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

@router.get("/delete-wrong-admin")
def delete_wrong_admin(db: Session = Depends(get_db)):
    """
    🗑️ Eliminar admin@financiamiento.com específicamente
    """
    try:
        logger.info("🗑️ Buscando admin@financiamiento.com para eliminar...")
        
        # Buscar el usuario incorrecto
        wrong_admin = db.query(User).filter(User.email == "admin@financiamiento.com").first()
        
        if not wrong_admin:
            logger.info("✅ admin@financiamiento.com no existe - OK")
            return {
                "message": "admin@financiamiento.com no existe",
                "status": "already_clean"
            }
        
        logger.info(f"🗑️ Eliminando: {wrong_admin.email} (ID: {wrong_admin.id})")
        
        # Eliminar el usuario
        db.delete(wrong_admin)
        db.commit()
        
        logger.info("✅ admin@financiamiento.com eliminado exitosamente")
        
        # Verificar que se eliminó
        remaining = db.query(User).filter(User.email == "admin@financiamiento.com").first()
        
        if remaining:
            raise HTTPException(status_code=500, detail="Error: El usuario aún existe después de eliminarlo")
        
        # Verificar usuarios restantes
        remaining_admins = db.query(User).filter(User.rol == "ADMINISTRADOR_GENERAL").all()
        
        result = {
            "message": "admin@financiamiento.com eliminado exitosamente",
            "deleted_user": {
                "email": wrong_admin.email,
                "id": wrong_admin.id
            },
            "remaining_admins": len(remaining_admins),
            "remaining_admin_details": []
        }
        
        for admin in remaining_admins:
            result["remaining_admin_details"].append({
                "email": admin.email,
                "id": admin.id,
                "active": admin.is_active
            })
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error eliminando usuario: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.get("/create-correct-admin")
def create_correct_admin(db: Session = Depends(get_db)):
    """
    📝 Crear itmaster@rapicreditca.com si no existe
    """
    try:
        logger.info("📝 Verificando itmaster@rapicreditca.com...")
        
        # Buscar el usuario correcto
        correct_admin = db.query(User).filter(User.email == "itmaster@rapicreditca.com").first()
        
        if correct_admin:
            logger.info("✅ itmaster@rapicreditca.com ya existe")
            return {
                "message": "itmaster@rapicreditca.com ya existe",
                "admin": {
                    "email": correct_admin.email,
                    "id": correct_admin.id,
                    "active": correct_admin.is_active,
                    "role": correct_admin.rol
                },
                "status": "already_exists"
            }
        
        logger.info("📝 Creando itmaster@rapicreditca.com...")
        
        # Crear el usuario correcto
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
        
        logger.info("✅ itmaster@rapicreditca.com creado exitosamente")
        
        return {
            "message": "itmaster@rapicreditca.com creado exitosamente",
            "admin": {
                "email": new_admin.email,
                "id": new_admin.id,
                "active": new_admin.is_active,
                "role": new_admin.rol
            },
            "login_credentials": {
                "email": "itmaster@rapicreditca.com",
                "password": "R@pi_2025**",
                "role": "ADMINISTRADOR_GENERAL"
            },
            "status": "created"
        }
        
    except Exception as e:
        logger.error(f"❌ Error creando usuario: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.get("/fix-admin-complete")
def fix_admin_complete(db: Session = Depends(get_db)):
    """
    🔧 Fix completo: eliminar incorrecto + crear correcto
    """
    try:
        logger.info("🔧 Iniciando fix completo de usuarios admin...")
        
        # 1. Eliminar admin@financiamiento.com
        wrong_admin = db.query(User).filter(User.email == "admin@financiamiento.com").first()
        
        if wrong_admin:
            logger.info(f"🗑️ Eliminando: {wrong_admin.email}")
            db.delete(wrong_admin)
            db.commit()
            deleted = True
        else:
            logger.info("✅ admin@financiamiento.com no existe")
            deleted = False
        
        # 2. Crear/verificar itmaster@rapicreditca.com
        correct_admin = db.query(User).filter(User.email == "itmaster@rapicreditca.com").first()
        
        if correct_admin:
            logger.info("✅ itmaster@rapicreditca.com ya existe")
            created = False
        else:
            logger.info("📝 Creando itmaster@rapicreditca.com...")
            
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
            correct_admin = new_admin
            created = True
        
        # 3. Estado final
        final_admins = db.query(User).filter(User.rol == "ADMINISTRADOR_GENERAL").all()
        
        result = {
            "message": "Fix completo ejecutado",
            "actions": {
                "deleted_wrong_admin": deleted,
                "created_correct_admin": created
            },
            "final_state": {
                "total_admins": len(final_admins),
                "admins": []
            },
            "login_credentials": {
                "email": "itmaster@rapicreditca.com",
                "password": "R@pi_2025**",
                "role": "ADMINISTRADOR_GENERAL"
            }
        }
        
        for admin in final_admins:
            result["final_state"]["admins"].append({
                "email": admin.email,
                "id": admin.id,
                "active": admin.is_active
            })
        
        logger.info("✅ Fix completo ejecutado exitosamente")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error en fix completo: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
