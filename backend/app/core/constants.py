# backend/app/core/constants.py
from enum import Enum


class UserRole(str, Enum):
    """Roles de usuario en el sistema"""
    ADMIN = "ADMIN"
    ASESOR = "ASESOR"
    COBRANZAS = "COBRANZAS"
    CONTADOR = "CONTADOR"


# Alias para compatibilidad
Roles = UserRole


class EstadoUsuario(str, Enum):
    """Estados de usuario"""
    ACTIVO = "ACTIVO"
    INACTIVO = "INACTIVO"
    SUSPENDIDO = "SUSPENDIDO"


class EstadoCliente(str, Enum):
    """Estados de cliente"""
    ACTIVO = "ACTIVO"
    INACTIVO = "INACTIVO"
    MOROSO = "MOROSO"
    BLOQUEADO = "BLOQUEADO"


class EstadoPrestamo(str, Enum):
    """Estados posibles de un préstamo"""
    PENDIENTE = "PENDIENTE"
    APROBADO = "APROBADO"
    RECHAZADO = "RECHAZADO"
    ACTIVO = "ACTIVO"
    PAGADO = "PAGADO"
    VENCIDO = "VENCIDO"
    CANCELADO = "CANCELADO"


class EstadoPago(str, Enum):
    """Estados posibles de un pago"""
    PENDIENTE = "PENDIENTE"
    CONFIRMADO = "CONFIRMADO"
    RECHAZADO = "RECHAZADO"


class TipoPrestamo(str, Enum):
    """Tipos de préstamo"""
    FRANCES = "FRANCES"  # Cuota fija
    ALEMAN = "ALEMAN"    # Amortización fija


class FrecuenciaPago(str, Enum):
    """Frecuencia de pago"""
    SEMANAL = "SEMANAL"
    QUINCENAL = "QUINCENAL"
    MENSUAL = "MENSUAL"


class TipoNotificacion(str, Enum):
    """Tipos de notificación"""
    EMAIL = "EMAIL"
    WHATSAPP = "WHATSAPP"
    SMS = "SMS"


class EstadoNotificacion(str, Enum):
    """Estados de notificación"""
    PENDIENTE = "PENDIENTE"
    ENVIADA = "ENVIADA"
    FALLIDA = "FALLIDA"


class TipoMovimiento(str, Enum):
    """Tipos de movimiento para auditoría"""
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class EstadoAprobacion(str, Enum):
    """Estados de aprobación"""
    PENDIENTE = "PENDIENTE"
    APROBADO = "APROBADO"
    RECHAZADO = "RECHAZADO"


class TipoPago(str, Enum):
    """Tipos de pago"""
    EFECTIVO = "EFECTIVO"
    TRANSFERENCIA = "TRANSFERENCIA"
    CHEQUE = "CHEQUE"
    TARJETA = "TARJETA"


# Configuraciones por defecto
DEFAULT_INTEREST_RATE = 0.02  # 2% mensual
DEFAULT_GRACE_DAYS = 3
MAX_LOAN_AMOUNT = 50000
MIN_LOAN_AMOUNT = 1000
