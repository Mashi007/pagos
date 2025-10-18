# backend/app/api/v1/endpoints/debug_refresh_user.py
"""
Endpoint de debug para verificar el problema de refreshUser
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.auth_service import AuthService
from app.schemas.user import UserMeResponse

router = APIRouter()

@router.get("/debug-refresh-user")
def debug_refresh_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Debug del problema de refreshUser que devuelve undefined
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
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
            "updated_at": current_user.updated_at.isoformat() if current_user.updated_at else None,
            "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
        }
        
        # 2. Verificar permisos
        try:
            permissions = AuthService.get_user_permissions(current_user)
            permissions_info = {
                "success": True,
                "permissions": permissions,
                "count": len(permissions)
            }
        except Exception as e:
            permissions_info = {
                "success": False,
                "error": str(e),
                "permissions": [],
                "count": 0
            }
        
        # 3. Crear UserMeResponse como lo hace el endpoint /me
        try:
            user_response = UserMeResponse(
                id=current_user.id,
                email=current_user.email,
                nombre=current_user.nombre,
                apellido=current_user.apellido,
                is_admin=current_user.is_admin,
                cargo=current_user.cargo,
                is_active=current_user.is_active,
                created_at=current_user.created_at,
                updated_at=current_user.updated_at,
                last_login=current_user.last_login,
                permissions=permissions
            )
            
            response_info = {
                "success": True,
                "user_response": user_response.dict(),
                "is_none": user_response is None
            }
        except Exception as e:
            response_info = {
                "success": False,
                "error": str(e),
                "user_response": None,
                "is_none": True
            }
        
        # 4. Verificar en base de datos directamente
        try:
            result = db.execute(text("""
                SELECT id, email, nombre, apellido, is_admin, is_active, created_at, updated_at, last_login
                FROM usuarios 
                WHERE id = :user_id
            """), {"user_id": current_user.id})
            
            db_user = result.fetchone()
            if db_user:
                db_info = {
                    "success": True,
                    "user": {
                        "id": db_user[0],
                        "email": db_user[1],
                        "nombre": db_user[2],
                        "apellido": db_user[3],
                        "is_admin": db_user[4],
                        "is_active": db_user[5],
                        "created_at": db_user[6].isoformat() if db_user[6] else None,
                        "updated_at": db_user[7].isoformat() if db_user[7] else None,
                        "last_login": db_user[8].isoformat() if db_user[8] else None,
                    }
                }
            else:
                db_info = {
                    "success": False,
                    "error": "Usuario no encontrado en BD",
                    "user": None
                }
        except Exception as e:
            db_info = {
                "success": False,
                "error": str(e),
                "user": None
            }
        
        return {
            "status": "success",
            "debug_info": {
                "current_user": user_info,
                "permissions": permissions_info,
                "user_response": response_info,
                "database_user": db_info,
                "summary": {
                    "user_exists": current_user is not None,
                    "is_admin": current_user.is_admin if current_user else False,
                    "permissions_ok": permissions_info["success"],
                    "response_ok": response_info["success"],
                    "db_ok": db_info["success"]
                }
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "debug_info": {
                "current_user": None,
                "permissions": {"success": False, "error": str(e)},
                "user_response": {"success": False, "error": str(e)},
                "database_user": {"success": False, "error": str(e)}
            }
        }

@router.get("/debug-user-permissions")
def debug_user_permissions(
    current_user: User = Depends(get_current_user)
):
    """
    Debug específico del sistema de permisos
    """
    try:
        # Importar funciones de permisos
        from app.core.permissions_simple import get_user_permissions, ADMIN_PERMISSIONS, USER_PERMISSIONS
        
        # Obtener permisos
        permissions = get_user_permissions(current_user.is_admin)
        permission_strings = [perm.value for perm in permissions]
        
        return {
            "status": "success",
            "user": {
                "id": current_user.id,
                "email": current_user.email,
                "is_admin": current_user.is_admin
            },
            "permissions": {
                "raw": permissions,
                "strings": permission_strings,
                "count": len(permissions)
            },
            "system_permissions": {
                "admin_permissions": [perm.value for perm in ADMIN_PERMISSIONS],
                "user_permissions": [perm.value for perm in USER_PERMISSIONS]
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "traceback": str(e.__traceback__)
        }
