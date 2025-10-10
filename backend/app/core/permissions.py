# backend/app/core/permissions.py
from typing import List
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.core.security import check_permission
from app.core.constants import EstadoUsuario


class PermissionChecker:
    """
    Verificador de permisos para endpoints
    
    Uso:
        @router.get("/clientes", dependencies=[Depends(PermissionChecker(["clientes.read"]))])
    """
    
    def __init__(self, required_permissions: List[str]):
        self.required_permissions = required_permissions
    
    def __call__(
        self,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        """Verificar permisos del usuario"""
        
        # Verificar que el usuario esté activo
        if current_user.estado != EstadoUsuario.ACTIVO:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario inactivo o suspendido"
            )
        
        # Verificar cada permiso requerido
        for permission in self.required_permissions:
            if not check_permission(current_user.rol, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"No tiene permiso para: {permission}"
                )
        
        return current_user


def require_role(allowed_roles: List[str]):
    """
    Decorador para requerir roles específicos
    
    Uso:
        @router.get("/admin", dependencies=[Depends(require_role(["ADMIN"]))])
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.rol not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rol no autorizado. Se requiere: {', '.join(allowed_roles)}"
            )
        return current_user
    
    return role_checker


def is_owner_or_admin(resource_user_id: int, current_user: User) -> bool:
    """
    Verificar si el usuario es dueño del recurso o es admin
    
    Útil para operaciones donde solo el dueño o admin pueden modificar
    """
    from app.core.constants import Roles
    
    return (
        current_user.id == resource_user_id or
        current_user.rol == Roles.ADMIN
    )
