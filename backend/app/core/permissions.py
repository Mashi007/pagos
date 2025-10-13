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
    COMERCIAL = "COMERCIAL"  # Rol para equipo comercial/ventas
    # ROLES AÑADIDOS PARA EL WORKFLOW DE APROBACIÓN DE PRÉSTAMOS
    GERENTE = "GERENTE"
    DIRECTOR = "DIRECTOR"
    COMITE = "COMITE"


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
        # Puede gestionar solo sus clientes asignados
        Permission.CLIENTE_CREATE,
        Permission.CLIENTE_READ,
        Permission.CLIENTE_UPDATE,  # ⚠️ Solo sus clientes + autorización Admin
        Permission.PRESTAMO_CREATE,
        Permission.PRESTAMO_READ,
        Permission.PRESTAMO_UPDATE,
        Permission.PAGO_READ,
        Permission.REPORTE_READ,
        Permission.KPI_READ,
        Permission.NOTIFICACION_READ,
        # NUEVOS PERMISOS ESPECÍFICOS
        Permission.CLIENTE_EDIT_OWN_WITH_AUTH,    # ⚠️ Solo sus clientes + autorización Admin
        Permission.CLIENTE_VIEW_OWN_ONLY,         # ✅ Solo puede ver sus clientes asignados
    ],
    
    UserRole.COBRANZAS: [
        # Puede gestionar clientes y pagos con algunas restricciones
        Permission.CLIENTE_CREATE,  # ✅ NUEVO: Crear clientes
        Permission.CLIENTE_READ,
        Permission.CLIENTE_UPDATE,  # ✅ NUEVO: Editar clientes
        Permission.PRESTAMO_READ,
        Permission.PAGO_CREATE,
        Permission.PAGO_READ,
        Permission.PAGO_UPDATE,     # ⚠️ Con aprobación para modificar montos
        Permission.PAGO_DELETE,     # ⚠️ Con aprobación para anular/eliminar
        Permission.REPORTE_READ,
        Permission.KPI_READ,
        Permission.NOTIFICACION_SEND,
        Permission.NOTIFICACION_READ,
        # NUEVOS PERMISOS ESPECÍFICOS
        Permission.PRESTAMO_MODIFY_AMORTIZATION,  # ⚠️ Con aprobación
        Permission.CLIENTE_CREATE_WITH_CREDIT,    # ✅ Ingresar clientes con crédito aprobado
        Permission.PAGO_MODIFY_WITH_APPROVAL,     # ⚠️ Modificar pagos con aprobación
        Permission.PAGO_DELETE_WITH_APPROVAL,     # ⚠️ Eliminar pagos con aprobación
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
    
    UserRole.COMERCIAL: [
        # Puede gestionar clientes con autorización admin para edición
        Permission.CLIENTE_CREATE,
        Permission.CLIENTE_READ,
        Permission.CLIENTE_UPDATE,  # ⚠️ Con autorización de Admin
        Permission.PRESTAMO_CREATE,
        Permission.PRESTAMO_READ,
        Permission.PRESTAMO_UPDATE,
        Permission.REPORTE_READ,  # Reportes limitados
        Permission.KPI_READ,
        Permission.NOTIFICACION_READ,
        # NUEVOS PERMISOS ESPECÍFICOS
        Permission.CLIENTE_EDIT_WITH_ADMIN_AUTH,  # ⚠️ Requiere autorización Admin
    ],

    # CONFIGURACIÓN DE ROLES PARA LA APROBACIÓN DE PRÉSTAMOS
    UserRole.GERENTE: [
        Permission.PRESTAMO_READ,       # Debe poder ver los detalles del préstamo
        Permission.PRESTAMO_APPROVE,    # Permiso general de aprobación
        Permission.CLIENTE_READ,
        Permission.REPORTE_READ,
        Permission.KPI_READ,
    ],

    UserRole.DIRECTOR: [
        Permission.PRESTAMO_READ,
        Permission.PRESTAMO_APPROVE,
        Permission.CLIENTE_READ,
        Permission.REPORTE_READ,
        Permission.KPI_READ,
        Permission.CONCILIACION_READ,
    ],

    UserRole.COMITE: [
        Permission.PRESTAMO_READ,
        Permission.PRESTAMO_APPROVE,
        Permission.CLIENTE_READ,
        Permission.REPORTE_READ,
        Permission.KPI_READ,
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


# ============================================
# FUNCIONES AUXILIARES PARA SISTEMA DE APROBACIONES
# ============================================

def can_edit_client_without_approval(user_role: str) -> bool:
    """
    Verificar si puede editar cliente sin solicitar aprobación
    """
    # Solo ADMIN puede editar sin aprobación
    return user_role == "ADMIN"


def can_modify_payment_without_approval(user_role: str) -> bool:
    """
    Verificar si puede modificar pagos sin solicitar aprobación
    """
    # Solo ADMIN puede modificar pagos sin aprobación
    return user_role == "ADMIN"


def can_view_all_clients(user_role: str) -> bool:
    """
    Verificar si puede ver todos los clientes o solo los asignados
    """
    # ASESOR solo ve sus clientes asignados
    if user_role == "ASESOR":
        return False
    
    # Otros roles pueden ver todos
    return user_role in ["ADMIN", "GERENTE", "DIRECTOR", "COBRANZAS", "COMERCIAL", "CONTADOR"]


def requires_admin_authorization(user_role: str, action: str) -> bool:
    """
    Verificar si una acción requiere autorización de Admin
    """
    # ADMIN no necesita autorización
    if user_role == "ADMIN":
        return False
    
    # Acciones que requieren autorización para ciertos roles
    authorization_required = {
        "edit_client": ["COMERCIAL", "ASESOR"],
        "modify_payment": ["COBRANZAS"],
        "delete_payment": ["COBRANZAS"],
        "modify_amortization": ["COBRANZAS"]
    }
    
    return user_role in authorization_required.get(action, [])


def get_client_filter_for_user(user_role: str, user_id: int):
    """
    Obtener filtro de clientes según el rol del usuario
    """
    # ASESOR solo ve sus clientes asignados
    if user_role == "ASESOR":
        return {"asesor_id": user_id}
    
    # Otros roles ven todos los clientes
    return None


def get_permission_matrix_summary() -> dict:
    """
    Obtener resumen de la matriz de permisos actualizada
    """
    return {
        "COBRANZAS": {
            "crear_editar_clientes": "✅ SÍ",
            "modificar_montos_pagos": "⚠️ SÍ (con solicitud de aprobación)",
            "anular_eliminar_pagos": "⚠️ SÍ (con solicitud de aprobación)",
            "modificar_tabla_amortizacion": "⚠️ SÍ (con solicitud de aprobación)",
            "ingresar_clientes_credito": "✅ SÍ"
        },
        "COMERCIAL": {
            "editar_clientes": "⚠️ SÍ (con autorización de Admin)"
        },
        "ASESOR": {
            "editar_clientes": "⚠️ SÍ (solo sus clientes, con autorización de Admin)"
        },
        "ADMIN": {
            "todas_las_acciones": "✅ SÍ (sin restricciones)"
        }
    }
