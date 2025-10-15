# backend/app/api/v1/endpoints/admin_system.py
"""
Endpoint para administración del sistema
Permite actualizar el administrador del sistema
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.session import get_db
from app.models.user import User
from app.core.security import get_password_hash
from app.core.permissions import UserRole, can_edit_users
from app.api.deps import get_current_user

router = APIRouter()


@router.post("/reset-admin-system")
def reset_admin_system(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🔧 Resetear sistema de usuarios - Solo para emergencias
    
    Elimina todos los usuarios y crea un nuevo administrador del sistema
    """
    try:
        # Verificar que el usuario actual puede hacer esta operación
        if not can_edit_users(current_user.rol):
            raise HTTPException(
                status_code=403,
                detail="No tienes permisos para realizar esta operación"
            )
        
        print("\n" + "="*70)
        print("🔧 RESETEO DEL SISTEMA DE USUARIOS")
        print("="*70 + "\n")
        
        # 1. Eliminar todos los usuarios existentes
        print("🗑️  ELIMINANDO USUARIOS EXISTENTES...")
        usuarios_existentes = db.query(User).all()
        
        if usuarios_existentes:
            print(f"   📊 Usuarios encontrados: {len(usuarios_existentes)}")
            for usuario in usuarios_existentes:
                print(f"   ❌ Eliminando: {usuario.email} ({usuario.rol})")
            
            # Eliminar todos los usuarios
            db.query(User).delete()
            db.commit()
            print("   ✅ Todos los usuarios eliminados")
        else:
            print("   ℹ️  No hay usuarios existentes")
        
        # 2. Crear nuevo administrador del sistema
        print("\n👑 CREANDO NUEVO ADMINISTRADOR DEL SISTEMA...")
        
        admin = User(
            email="itmaster@rapicreditca.com",
            nombre="IT",
            apellido="Master",
            hashed_password=get_password_hash("R@pi_2025**"),
            rol=UserRole.ADMINISTRADOR_GENERAL,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
        print("✅ Administrador del sistema creado exitosamente\n")
        
        # 3. Verificar sistema
        total_usuarios = db.query(User).count()
        print(f"🔍 VERIFICACIÓN: Total usuarios: {total_usuarios}")
        
        admin_verificado = db.query(User).filter(
            User.email == "itmaster@rapicreditca.com",
            User.is_active == True
        ).first()
        
        if admin_verificado and total_usuarios == 1:
            print("✅ Sistema verificado y listo")
        else:
            print("❌ Error en verificación del sistema")
        
        return {
            "success": True,
            "message": "Sistema de usuarios reseteado exitosamente",
            "admin_created": {
                "email": admin.email,
                "nombre": admin.full_name,
                "rol": admin.rol,
                "is_active": admin.is_active,
                "id": admin.id
            },
            "total_users": total_usuarios,
            "credentials": {
                "email": "itmaster@rapicreditca.com",
                "password": "R@pi_2025**"
            },
            "access_info": {
                "login_url": "/api/v1/auth/login",
                "dashboard_url": "/api/v1/dashboard/admin",
                "docs_url": "/docs"
            }
        }
        
    except Exception as e:
        print(f"\n❌ Error reseteando sistema: {e}\n")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error reseteando sistema: {str(e)}"
        )


@router.get("/system-status")
def get_system_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📊 Obtener estado del sistema de usuarios
    """
    try:
        # Contar usuarios por rol
        total_users = db.query(User).count()
        
        users_by_role = {}
        for role in UserRole:
            count = db.query(User).filter(User.rol == role).count()
            users_by_role[role.value] = count
        
        # Verificar administrador activo
        admin_active = db.query(User).filter(
            User.rol == UserRole.ADMINISTRADOR_GENERAL,
            User.is_active == True
        ).first()
        
        return {
            "total_users": total_users,
            "users_by_role": users_by_role,
            "admin_active": {
                "exists": admin_active is not None,
                "email": admin_active.email if admin_active else None,
                "name": admin_active.full_name if admin_active else None
            },
            "system_secure": total_users > 0 and admin_active is not None,
            "current_user": {
                "email": current_user.email,
                "rol": current_user.rol,
                "is_active": current_user.is_active
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo estado del sistema: {str(e)}"
        )


@router.post("/verify-login-system")
def verify_login_system(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🔍 Verificar que el sistema de login funciona correctamente
    """
    try:
        # Verificar que solo existe el administrador
        usuarios = db.query(User).all()
        
        verification_results = {
            "total_users": len(usuarios),
            "only_admin_exists": len(usuarios) == 1,
            "admin_details": None,
            "security_status": "SECURE" if len(usuarios) == 1 else "COMPROMISED",
            "recommendations": []
        }
        
        if len(usuarios) == 1:
            admin = usuarios[0]
            verification_results["admin_details"] = {
                "email": admin.email,
                "rol": admin.rol,
                "is_active": admin.is_active,
                "created_at": admin.created_at
            }
            
            if admin.email == "itmaster@rapicreditca.com":
                verification_results["recommendations"].append("✅ Administrador correcto configurado")
            else:
                verification_results["recommendations"].append("⚠️ Administrador con email diferente al esperado")
                
        else:
            verification_results["recommendations"].append("❌ Múltiples usuarios encontrados - sistema comprometido")
            for usuario in usuarios:
                verification_results["recommendations"].append(f"   - {usuario.email} ({usuario.rol})")
        
        return verification_results
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error verificando sistema de login: {str(e)}"
        )
