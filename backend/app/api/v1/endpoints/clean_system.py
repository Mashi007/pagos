"""
Endpoint definitivo para limpiar el sistema
ELIMINA admin@financiamiento.com y asegura configuración correcta
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

@router.post("/clean-admin-users")
def clean_admin_users(db: Session = Depends(get_db)):
    """
    🧹 LIMPIEZA DEFINITIVA: Eliminar admin@financiamiento.com y configurar itmaster@rapicreditca.com
    """
    try:
        logger.info("🧹 Iniciando limpieza definitiva de usuarios administradores...")
        
        # 1. Buscar todos los usuarios administradores
        admins = db.query(User).filter(User.rol == "ADMINISTRADOR_GENERAL").all()
        
        logger.info(f"📋 Encontrados {len(admins)} usuarios administradores")
        
        result = {
            "found_admins": len(admins),
            "admin_details": [],
            "actions_taken": [],
            "final_state": {}
        }
        
        # Detalles de admins encontrados
        for admin in admins:
            result["admin_details"].append({
                "id": admin.id,
                "email": admin.email,
                "active": admin.is_active,
                "role": admin.rol
            })
        
        # 2. Eliminar admin@financiamiento.com si existe
        old_admin = db.query(User).filter(User.email == "admin@financiamiento.com").first()
        
        if old_admin:
            logger.info(f"🗑️ Eliminando usuario incorrecto: {old_admin.email}")
            db.delete(old_admin)
            db.commit()
            result["actions_taken"].append(f"Eliminado: {old_admin.email}")
        else:
            logger.info("✅ No existe admin@financiamiento.com - OK")
            result["actions_taken"].append("admin@financiamiento.com no existía")
        
        # 3. Verificar/crear itmaster@rapicreditca.com
        correct_admin = db.query(User).filter(User.email == "itmaster@rapicreditca.com").first()
        
        if correct_admin:
            logger.info(f"✅ Usuario correcto ya existe: {correct_admin.email}")
            
            # Asegurar configuración correcta
            needs_update = False
            
            if not correct_admin.is_active:
                correct_admin.is_active = True
                needs_update = True
                
            if correct_admin.rol != "ADMINISTRADOR_GENERAL":
                correct_admin.rol = "ADMINISTRADOR_GENERAL"
                needs_update = True
            
            if needs_update:
                db.commit()
                db.refresh(correct_admin)
                result["actions_taken"].append("Actualizado: itmaster@rapicreditca.com")
            else:
                result["actions_taken"].append("Verificado: itmaster@rapicreditca.com ya estaba correcto")
                
        else:
            logger.info("📝 Creando usuario correcto: itmaster@rapicreditca.com")
            
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
            
            result["actions_taken"].append("Creado: itmaster@rapicreditca.com")
        
        # 4. Estado final
        final_admins = db.query(User).filter(User.rol == "ADMINISTRADOR_GENERAL").all()
        
        result["final_state"] = {
            "total_admins": len(final_admins),
            "admins": []
        }
        
        for admin in final_admins:
            result["final_state"]["admins"].append({
                "email": admin.email,
                "active": admin.is_active,
                "role": admin.rol
            })
        
        # 5. Verificar que no queden referencias a admin@financiamiento.com
        remaining_old = db.query(User).filter(User.email == "admin@financiamiento.com").first()
        
        if remaining_old:
            raise HTTPException(status_code=500, detail="Error: Aún existe admin@financiamiento.com")
        
        logger.info("✅ Limpieza completada exitosamente")
        
        return {
            "message": "Limpieza definitiva completada",
            "status": "success",
            "data": result,
            "login_credentials": {
                "email": "itmaster@rapicreditca.com",
                "password": "R@pi_2025**",
                "role": "ADMINISTRADOR_GENERAL"
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error en limpieza: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.get("/system-status")
def get_system_status(db: Session = Depends(get_db)):
    """
    📊 Estado actual del sistema de usuarios
    """
    try:
        admins = db.query(User).filter(User.rol == "ADMINISTRADOR_GENERAL").all()
        
        status = {
            "total_admins": len(admins),
            "admins": [],
            "has_correct_admin": False,
            "has_incorrect_admin": False
        }
        
        for admin in admins:
            admin_info = {
                "id": admin.id,
                "email": admin.email,
                "active": admin.is_active,
                "role": admin.rol,
                "created_at": admin.created_at.isoformat() if admin.created_at else None
            }
            status["admins"].append(admin_info)
            
            if admin.email == "itmaster@rapicreditca.com":
                status["has_correct_admin"] = True
            elif admin.email == "admin@financiamiento.com":
                status["has_incorrect_admin"] = True
        
        status["system_ready"] = status["has_correct_admin"] and not status["has_incorrect_admin"]
        
        return {
            "message": "Estado del sistema",
            "status": status
        }
        
    except Exception as e:
        logger.error(f"❌ Error verificando estado: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
