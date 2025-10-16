"""
Sistema de permisos y roles
Define los roles del sistema y sus permisos
"""
from enum import Enum
from typing import List


class UserRole(str, Enum):
    """Rol único del sistema - todos tienen acceso completo"""
    USER = "USER"


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
    PRESTAMO_APPROVE = "prestamo:approve" # Permiso general de aprobación
    
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
    
    # NUEVOS PERMISOS ESPECÍFICOS PARA SISTEMA DE APROBACIONES
    PRESTAMO_MODIFY_AMORTIZATION = "prestamo:modify_amortization"
    CLIENTE_CREATE_WITH_CREDIT = "cliente:create_with_credit"
    CLIENTE_EDIT_WITH_ADMIN_AUTH = "cliente:edit_with_admin_auth"
    CLIENTE_EDIT_OWN_WITH_AUTH = "cliente:edit_own_with_auth"
    CLIENTE_VIEW_OWN_ONLY = "cliente:view_own_only"
    PAGO_MODIFY_WITH_APPROVAL = "pago:modify_with_approval"
    PAGO_DELETE_WITH_APPROVAL = "pago:delete_with_approval"


# Mapeo de roles a permisos
ROLE_PERMISSIONS: dict[UserRole, List[Permission]] = {
    UserRole.ADMINISTRADOR_GENERAL: [
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
    
    UserRole.COBRANZAS: [
        # Acceso completo EXCEPTO editar usuarios y auditoría
        Permission.USER_CREATE,  # Puede crear usuarios
        Permission.USER_READ,    # Puede ver usuarios
        Permission.USER_DELETE,  # Puede eliminar usuarios
        # NO tiene USER_UPDATE - no puede editar usuarios
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
        # NO tiene AUDITORIA_READ - no puede acceder a auditoría
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


# ============================================
# FUNCIONES AUXILIARES PARA SISTEMA DE APROBACIONES
# ============================================

def can_edit_users(user_role: str) -> bool:
    """
    Verificar si puede editar usuarios
    """
    # Solo ADMINISTRADOR_GENERAL puede editar usuarios
    return user_role == "ADMINISTRADOR_GENERAL"


def can_access_audit_tools(user_role: str) -> bool:
    """
    Verificar si puede acceder a herramientas de auditoría
    """
    # Solo ADMINISTRADOR_GENERAL puede acceder a auditoría
    return user_role == "ADMINISTRADOR_GENERAL"


def can_view_all_clients(user_role: str) -> bool:
    """
    Verificar si puede ver todos los clientes
    """
    # Todos los roles pueden ver todos los clientes
    return True


def requires_admin_authorization(user_role: str, action: str) -> bool:
    """
    Verificar si una acción requiere autorización de Admin
    """
    # ADMINISTRADOR_GENERAL no necesita autorización
    if user_role == "ADMINISTRADOR_GENERAL":
        return False
    
    # COBRANZAS no necesita autorización para acciones permitidas
    return False


def get_client_filter_for_user(user_role: str, user_id: int):
    """
    Obtener filtro de clientes según el rol del usuario
    """
    # Todos los roles ven todos los clientes
    return None


def get_permission_matrix_summary() -> dict:
    """
    Obtener resumen de la matriz de permisos actualizada
    """
    return {
        "ADMINISTRADOR_GENERAL": {
            "editar_usuarios": "✅ SÍ",
            "acceder_auditoria": "✅ SÍ",
            "todas_las_acciones": "✅ SÍ (sin restricciones)"
        },
        "COBRANZAS": {
            "editar_usuarios": "❌ NO",
            "acceder_auditoria": "❌ NO",
            "crear_usuarios": "✅ SÍ",
            "eliminar_usuarios": "✅ SÍ",
            "ver_usuarios": "✅ SÍ",
            "todas_las_demas_acciones": "✅ SÍ"
        }
    }
