"""
Sistema de permisos simplificado
Solo 2 roles: ADMIN (acceso completo) y USER (acceso limitado)
"""
from enum import Enum
from typing import List


class Permission(str, Enum):
    """Permisos del sistema - simplificado"""
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
    
    # Pagos
    PAGO_CREATE = "pago:create"
    PAGO_READ = "pago:read"
    PAGO_UPDATE = "pago:update"
    PAGO_DELETE = "pago:delete"
    
    # Reportes
    REPORTE_READ = "reporte:read"
    
    # Auditoría
    AUDITORIA_READ = "auditoria:read"
    
    # Configuración
    CONFIG_READ = "config:read"
    CONFIG_UPDATE = "config:update"


# Mapeo simplificado: Solo ADMIN tiene todos los permisos
ADMIN_PERMISSIONS = [
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
    Permission.PAGO_CREATE,
    Permission.PAGO_READ,
    Permission.PAGO_UPDATE,
    Permission.PAGO_DELETE,
    Permission.REPORTE_READ,
    Permission.AUDITORIA_READ,
    Permission.CONFIG_READ,
    Permission.CONFIG_UPDATE,
]

# USER solo tiene permisos básicos
USER_PERMISSIONS = [
    Permission.CLIENTE_READ,
    Permission.PRESTAMO_READ,
    Permission.PAGO_READ,
    Permission.REPORTE_READ,
]


def has_permission(user_is_admin: bool, permission: Permission) -> bool:
    """
    Verificar si un usuario tiene un permiso específico
    
    Args:
        user_is_admin: True si es admin, False si es user
        permission: Permiso a verificar
    
    Returns:
        True si tiene el permiso, False en caso contrario
    """
    if user_is_admin:
        return permission in ADMIN_PERMISSIONS
    else:
        return permission in USER_PERMISSIONS


def get_user_permissions(user_is_admin: bool) -> List[Permission]:
    """
    Obtener todos los permisos de un usuario
    
    Args:
        user_is_admin: True si es admin, False si es user
    
    Returns:
        Lista de permisos del usuario
    """
    if user_is_admin:
        return ADMIN_PERMISSIONS
    else:
        return USER_PERMISSIONS
