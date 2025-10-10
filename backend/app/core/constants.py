# backend/app/core/constants.py
from enum import Enum


class Roles(str, Enum):
    """Roles del sistema"""
    ADMIN = "ADMIN"
    COBRANZA = "COBRANZA"
    ASESOR = "ASESOR"
    CONTADOR = "CONTADOR"


class EstadoUsuario(str, Enum):
    """Estados de usuario"""
    ACTIVO = "ACTIVO"
    INACTIVO = "INACTIVO"
    SUSPENDIDO = "SUSPENDIDO"


class TipoNotificacion(str, Enum):
    """Tipos de notificación"""
    EMAIL = "EMAIL"
    WHATSAPP = "WHATSAPP"
    SISTEMA = "SISTEMA"


class EstadoNotificacion(str, Enum):
    """Estados de notificación"""
    PENDIENTE = "PENDIENTE"
    ENVIADA = "ENVIADA"
    FALLIDA = "FALLIDA"


class TipoMovimiento(str, Enum):
    """Tipos de movimiento de auditoría"""
    CREACION = "CREACION"
    ACTUALIZACION = "ACTUALIZACION"
    ELIMINACION = "ELIMINACION"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"


class EstadoAprobacion(str, Enum):
    """Estados de aprobación"""
    PENDIENTE = "PENDIENTE"
    APROBADO = "APROBADO"
    RECHAZADO = "RECHAZADO"


# Permisos por módulo
PERMISOS = {
    Roles.ADMIN: [
        "clientes.*",
        "prestamos.*",
        "pagos.*",
        "usuarios.*",
        "reportes.*",
        "configuracion.*",
        "aprobaciones.*",
        "conciliacion.*",
        "kpis.*"
    ],
    Roles.COBRANZA: [
        "clientes.read",
        "clientes.update",
        "prestamos.read",
        "pagos.*",
        "reportes.read",
        "conciliacion.read",
        "kpis.read"
    ],
    Roles.ASESOR: [
        "clientes.*",
        "prestamos.create",
        "prestamos.read",
        "pagos.read",
        "reportes.read"
    ],
    Roles.CONTADOR: [
        "clientes.read",
        "prestamos.read",
        "pagos.read",
        "reportes.*",
        "conciliacion.*",
        "kpis.*"
    ]
}

# Configuración de notificaciones
DIAS_RECORDATORIO = [3, 1]  # Días antes del vencimiento
DIAS_MORA = [1, 3, 5]  # Días después del vencimiento

# Configuración de validadores
MONTO_MINIMO_PRESTAMO = 1000
MONTO_MAXIMO_PRESTAMO = 1000000
CUOTAS_MINIMAS = 1
CUOTAS_MAXIMAS = 60
