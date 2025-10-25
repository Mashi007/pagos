"""
Solo 2 roles: ADMIN (acceso completo) y USER (acceso limitado)
"""

from enum import Enum
from typing import List


class Permission(str, Enum):

    # Dashboard
    VIEW_DASHBOARD = "dashboard:view"

    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"

    # Clientes
    CLIENTE_CREATE = "cliente:create"
    CLIENTE_READ = "cliente:read"
    CLIENTE_UPDATE = "cliente:update"
    CLIENTE_DELETE = "cliente:delete"

    PRESTAMO_CREATE = "prestamo:create"
    PRESTAMO_READ = "prestamo:read"
    PRESTAMO_UPDATE = "prestamo:update"
    PRESTAMO_DELETE = "prestamo:delete"
    PRESTAMO_APPROVE = "prestamo:approve"

    PAGO_CREATE = "pago:create"
    PAGO_READ = "pago:read"
    PAGO_UPDATE = "pago:update"
    PAGO_DELETE = "pago:delete"

    # Reportes
    REPORTE_READ = "reporte:read"

    # Auditoría
    AUDIT_READ = "audit:read"

    # Configuración
    CONFIG_READ = "config:read"
    CONFIG_UPDATE = "config:update"
    CONFIG_MANAGE = "config:manage"

    # Analistas
    ANALISTA_CREATE = "analista:create"
    ANALISTA_READ = "analista:read"
    ANALISTA_UPDATE = "analista:update"
    ANALISTA_DELETE = "analista:delete"

    CONCESIONARIO_CREATE = "concesionario:create"
    CONCESIONARIO_READ = "concesionario:read"
    CONCESIONARIO_UPDATE = "concesionario:update"
    CONCESIONARIO_DELETE = "concesionario:delete"

    MODELO_CREATE = "modelo:create"
    MODELO_READ = "modelo:read"
    MODELO_UPDATE = "modelo:update"
    MODELO_DELETE = "modelo:delete"

    # Validadores
    VALIDADOR_CREATE = "validador:create"
    VALIDADOR_READ = "validador:read"
    VALIDADOR_UPDATE = "validador:update"
    VALIDADOR_DELETE = "validador:delete"


ADMIN_PERMISSIONS: List[Permission] = [
    # Dashboard
    Permission.VIEW_DASHBOARD,

    Permission.USER_CREATE,
    Permission.USER_READ,
    Permission.USER_UPDATE,
    Permission.USER_DELETE,

    # Clientes - Gestión completa
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

    # Reportes
    Permission.REPORTE_READ,

    # Auditoría
    Permission.AUDIT_READ,

    # Configuración - Gestión completa
    Permission.CONFIG_READ,
    Permission.CONFIG_UPDATE,
    Permission.CONFIG_MANAGE,

    # Analistas - Gestión completa
    Permission.ANALISTA_CREATE,
    Permission.ANALISTA_READ,
    Permission.ANALISTA_UPDATE,
    Permission.ANALISTA_DELETE,

    Permission.CONCESIONARIO_CREATE,
    Permission.CONCESIONARIO_READ,
    Permission.CONCESIONARIO_UPDATE,
    Permission.CONCESIONARIO_DELETE,

    Permission.MODELO_CREATE,
    Permission.MODELO_READ,
    Permission.MODELO_UPDATE,
    Permission.MODELO_DELETE,

    # Validadores - Gestión completa
    Permission.VALIDADOR_CREATE,
    Permission.VALIDADOR_READ,
    Permission.VALIDADOR_UPDATE,
    Permission.VALIDADOR_DELETE,
]


USER_PERMISSIONS: List[Permission] = [
    # Dashboard básico
    Permission.VIEW_DASHBOARD,

    Permission.CLIENTE_READ,
    Permission.PRESTAMO_READ,
    Permission.PAGO_READ,
    Permission.REPORTE_READ,

    # operaciones básicas
    Permission.CLIENTE_CREATE,  # ✅ Crear clientes
    Permission.CLIENTE_UPDATE,  # ✅ Actualizar clientes
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

    Args:
        user_is_admin: True si es admin, False si es user

    Returns:
    """
    if user_is_admin:
        return ADMIN_PERMISSIONS
    else:
        return USER_PERMISSIONS
