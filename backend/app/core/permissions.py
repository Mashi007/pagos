# backend/app/core/permissions.py
from enum import Enum
from typing import List
from fastapi import HTTPException, status


class UserRole(str, Enum):
    """Roles de usuario en el sistema"""
    ADMIN = "ADMIN"
    ASESOR = "ASESOR"
    COBRANZAS = "COBRANZAS"
    CONTADOR = "CONTADOR"


class Permission(str, Enum):
    """Permisos del sistema"""
    # Clientes
    CLIENTE_CREATE = "cliente:create"
    CLIENTE_READ = "cliente:read"
    CLIENTE_UPDATE = "cliente:update"
    CLIENTE_DELETE = "cliente:delete"
    
    # Préstamos
    PRESTAMO_CREATE = "prestamo:create"
    PRESTAMO_READ = "prestamo:read"
    PRESTAMO_UPDATE = "prestamo:update"
    PRESTAMO_DELETE = "prestamo:delete"
    PRESTAMO_APPROVE = "prestamo:approve"
    
    # Pagos
    PAGO_CREATE = "pago:create"
    PAGO_READ = "pago:read"
    PAGO_UPDATE = "pago:update"
    PAGO_DELETE = "pago:delete"
    
    # Usuarios
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    
    # Reportes
    REPORTE_READ = "reporte:read"
    REPORTE_EXPORT = "reporte:export"
    
    # Configuración
    CONFIG_READ = "config:read"
    CONFIG_UPDATE = "config:update"


# Mapeo de roles a permisos
ROLE_PERMISSIONS = {
    UserRole.ADMIN: [
        # Todos los permisos
        Permission.CLIENTE_CREATE,
        Permission.CLIENTE_READ,
        Permission.CLIENTE_UPDATE,
        Permission.CLIENTE_DELETE,
        Permission.PRESTAMO_CREATE,
        Permission.PRESTAMO_READ,
        Permission.PRESTAMO_UPDATE,
        Permission.PRESTAMO_DELETE,
        Permission.PRESTAMO_APPROVE,
        Permission.PAGO_CREATE,
        Permission.PAGO_READ,
        Permission.PAGO_UPDATE,
        Permission.PAGO_DELETE,
        Permission.USER_CREATE,
        Permission.USER_READ,
        Permission.USER_UPDATE,
        Permission.USER_DELETE,
        Permission.REPORTE_READ,
        Permission.REPORTE_EXPORT,
        Permission.CONFIG_READ,
        Permission.CONFIG_UPDATE,
    ],
    
    UserRole.ASESOR: [
        # Clientes y préstamos (crear, leer, actualizar)
        Permission.CLIENTE_CREATE,
        Permission.CLIENTE_READ,
        Permission.CLIENTE_UPDATE,
        Permission.PRESTAMO_CREATE,
        Permission.PRESTAMO_READ,
        Permission.PRESTAMO_UPDATE,
        Permission.PAGO_READ,
        Permission.REPORTE_READ,
    ],
    
    UserRole.COBRANZAS: [
        # Pagos y reportes
        Permission.CLIENTE_READ,
        Permission.PRESTAMO_READ,
        Permission.PAGO_CREATE,
        Permission.PAGO_READ,
        Permission.PAGO_UPDATE,
        Permission.REPORTE_READ,
        Permission.REPORTE_EXPORT,
    ],
    
    UserRole.CONTADOR: [
        # Solo lectura y reportes
        Permission.CLIENTE_READ,
        Permission.PRESTAMO_READ,
        Permission.PAGO_READ,
        Permission.REPORTE_READ,
        Permission.REPORTE_EXPORT,
    ],
}


def check_permission(user_role: str, required_permission: Permission) -> bool:
    """
    Verificar si un rol tiene un permiso específico
    
    Args:
        user_role: Rol del usuario
        required_permission: Permiso requerido
    
    Returns:
        True si tiene el permiso, False si no
    """
    role = UserRole(user_role)
    permissions = ROLE_PERMISSIONS.get(role, [])
    return required_permission in permissions


def require_permission(required_permission: Permission):
    """
    Decorator para requerir un permiso específico
    
    Usage:
        @require_permission(Permission.CLIENTE_CREATE)
        def crear_cliente(...):
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # El usuario actual debe estar en kwargs como 'current_user'
            current_user = kwargs.get('current_user')
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="No autenticado"
                )
            
            if not check_permission(current_user.rol, required_permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"No tiene permiso para: {required_permission.value}"
                )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_roles(allowed_roles: List[UserRole]):
    """
    Decorator para requerir uno de varios roles
    
    Usage:
        @require_roles([UserRole.ADMIN, UserRole.ASESOR])
        def crear_prestamo(...):
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="No autenticado"
                )
            
            if current_user.rol not in [role.value for role in allowed_roles]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Rol no autorizado. Se requiere: {', '.join([r.value for r in allowed_roles])}"
                )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator
