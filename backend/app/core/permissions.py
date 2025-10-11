# backend/app/core/permissions.py
"""
Sistema de permisos y roles
Define los roles del sistema y sus permisos
"""
from enum import Enum
from typing import List


class UserRole(str, Enum):
    """Roles de usuario del sistema"""
    ADMIN = "ADMIN"
    ASESOR = "ASESOR"
    COBRANZAS = "COBRANZAS"
    CONTADOR = "CONTADOR"


class Permission(str, Enum):
    """Permisos del sistema"""
    # Usuarios
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    
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
    
    # Reportes
    REPORTE_READ = "reporte:read"
    REPORTE_CREATE = "reporte:create"
    
    # KPIs
    KPI_READ = "kpi:read"
    
    # Conciliación
    CONCILIACION_CREATE = "conciliacion:create"
    CONCILIACION_READ = "conciliacion:read"
    CONCILIACION_APPROVE = "conciliacion:approve"
    
    # Notificaciones
    NOTIFICACION_SEND = "notificacion:send"
    NOTIFICACION_READ = "notificacion:read"
    
    # Configuración
    CONFIG_READ = "config:read"
    CONFIG_UPDATE = "config:update"
    
    # Auditoría
    AUDITORIA_READ = "auditoria:read"


# Mapeo de roles a permisos
ROLE_PERMISSIONS: dict[UserRole, List[Permission]] = {
    UserRole.ADMIN: [
        # Acceso total - todos los permisos
        Permission.USER_CREATE,
        Permission.USER_READ,
        Permission.USER_UPDATE,
        Permission.USER_DELETE,
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
        Permission.REPORTE_READ,
        Permission.REPORTE_CREATE,
        Permission.KPI_READ,
        Permission.CONCILIACION_CREATE,
        Permission.CONCILIACION_READ,
        Permission.CONCILIACION_APPROVE,
        Permission.NOTIFICACION_SEND,
        Permission.NOTIFICACION_READ,
        Permission.CONFIG_READ,
        Permission.CONFIG_UPDATE,
        Permission.AUDITORIA_READ,
    ],
    
    UserRole.ASESOR: [
        # Puede crear y gestionar clientes y préstamos
        Permission.CLIENTE_CREATE,
        Permission.CLIENTE_READ,
        Permission.CLIENTE_UPDATE,
        Permission.PRESTAMO_CREATE,
        Permission.PRESTAMO_READ,
        Permission.PRESTAMO_UPDATE,
        Permission.PAGO_READ,
        Permission.REPORTE_READ,
        Permission.KPI_READ,
        Permission.NOTIFICACION_READ,
    ],
    
    UserRole.COBRANZAS: [
        # Puede ver cartera y registrar pagos
        Permission.CLIENTE_READ,
        Permission.PRESTAMO_READ,
        Permission.PAGO_CREATE,
        Permission.PAGO_READ,
        Permission.PAGO_UPDATE,
        Permission.REPORTE_READ,
        Permission.KPI_READ,
        Permission.NOTIFICACION_SEND,
        Permission.NOTIFICACION_READ,
    ],
    
    UserRole.CONTADOR: [
        # Solo lectura de reportes y KPIs
        Permission.CLIENTE_READ,
        Permission.PRESTAMO_READ,
        Permission.PAGO_READ,
        Permission.REPORTE_READ,
        Permission.REPORTE_CREATE,
        Permission.KPI_READ,
        Permission.CONCILIACION_READ,
        Permission.AUDITORIA_READ,
    ],
}


def get_role_permissions(role: UserRole) -> List[Permission]:
    """
    Obtiene los permisos asociados a un rol
    
    Args:
        role: Rol del usuario
        
    Returns:
        Lista de permisos del rol
    """
    return ROLE_PERMISSIONS.get(role, [])


def has_permission(role: UserRole, permission: Permission) -> bool:
    """
    Verifica si un rol tiene un permiso específico
    
    Args:
        role: Rol del usuario
        permission: Permiso a verificar
        
    Returns:
        True si el rol tiene el permiso
    """
    role_perms = get_role_permissions(role)
    return permission in role_perms


def has_any_permission(role: UserRole, permissions: List[Permission]) -> bool:
    """
    Verifica si un rol tiene al menos uno de los permisos especificados
    
    Args:
        role: Rol del usuario
        permissions: Lista de permisos a verificar
        
    Returns:
        True si el rol tiene al menos un permiso de la lista
    """
    role_perms = get_role_permissions(role)
    return any(perm in role_perms for perm in permissions)


def has_all_permissions(role: UserRole, permissions: List[Permission]) -> bool:
    """
    Verifica si un rol tiene todos los permisos especificados
    
    Args:
        role: Rol del usuario
        permissions: Lista de permisos a verificar
        
    Returns:
        True si el rol tiene todos los permisos de la lista
    """
    role_perms = get_role_permissions(role)
    return all(perm in role_perms for perm in permissions)


def get_permissions_by_module(role: UserRole, module: str) -> List[Permission]:
    """
    Obtiene los permisos de un rol para un módulo específico
    
    Args:
        role: Rol del usuario
        module: Nombre del módulo (cliente, prestamo, pago, etc.)
        
    Returns:
        Lista de permisos del rol para ese módulo
    """
    role_perms = get_role_permissions(role)
    return [perm for perm in role_perms if perm.value.startswith(f"{module}:")]
