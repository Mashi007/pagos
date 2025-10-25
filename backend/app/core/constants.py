# backend/app/core/constants.py

from enum import Enum

# ✅ ELIMINADO: Import de UserRole -
# ahora se usa sistema simplificado con is_admin
# from app.core.permissions import UserRole
# Roles = UserRole


class EstadoUsuario(str, Enum):
    ACTIVO = "ACTIVO"
    INACTIVO = "INACTIVO"
    SUSPENDIDO = "SUSPENDIDO"


class EstadoCliente(str, Enum):
    ACTIVO = "ACTIVO"
    INACTIVO = "INACTIVO"
    MOROSO = "MOROSO"
    BLOQUEADO = "BLOQUEADO"


class EstadoPrestamo(str, Enum):
    PENDIENTE = "PENDIENTE"
    APROBADO = "APROBADO"
    RECHAZADO = "RECHAZADO"
    ACTIVO = "ACTIVO"
    PAGADO = "PAGADO"
    VENCIDO = "VENCIDO"
    CANCELADO = "CANCELADO"


class EstadoPago(str, Enum):
    PENDIENTE = "PENDIENTE"
    CONFIRMADO = "CONFIRMADO"
    RECHAZADO = "RECHAZADO"


class TipoPrestamo(str, Enum):
    FRANCES = "FRANCES"  # Cuota fija
    ALEMAN = "ALEMAN"  # Amortización fija


class FrecuenciaPago(str, Enum):
    """Frecuencia de pago"""
    SEMANAL = "SEMANAL"
    QUINCENAL = "QUINCENAL"
    MENSUAL = "MENSUAL"


class TipoNotificacion(str, Enum):
    EMAIL = "EMAIL"
    WHATSAPP = "WHATSAPP"
    SMS = "SMS"


class EstadoNotificacion(str, Enum):
    PENDIENTE = "PENDIENTE"
    ENVIADA = "ENVIADA"
    FALLIDA = "FALLIDA"


class TipoMovimiento(str, Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class EstadoAprobacion(str, Enum):
    PENDIENTE = "PENDIENTE"
    APROBADA = "APROBADA"
    RECHAZADA = "RECHAZADA"
    CANCELADA = "CANCELADA"


class TipoPago(str, Enum):
    EFECTIVO = "EFECTIVO"
    TRANSFERENCIA = "TRANSFERENCIA"
    CHEQUE = "CHEQUE"
    TARJETA = "TARJETA"

# ✅ AGREGADAS LAS CLASES FALTANTES


class MetodoPago(str, Enum):
    EFECTIVO = "EFECTIVO"
    TRANSFERENCIA = "TRANSFERENCIA"
    CHEQUE = "CHEQUE"
    TARJETA = "TARJETA"


class TipoDocumento(str, Enum):
    CEDULA = "CEDULA"
    RUC = "RUC"
    PASAPORTE = "PASAPORTE"


class TipoInteres(str, Enum):
    SIMPLE = "SIMPLE"
    COMPUESTO = "COMPUESTO"


class EstadoConciliacion(str, Enum):
    PENDIENTE = "PENDIENTE"
    CONCILIADO = "CONCILIADO"
    DESCUADRADO = "DESCUADRADO"
    REVISADO = "REVISADO"

# Constantes de valores por defecto
DEFAULT_INTEREST_RATE = 0.02  # 2% mensual
DEFAULT_GRACE_DAYS = 3
DEFAULT_MAX_LOAN_AMOUNT = 50000
DEFAULT_MIN_LOAN_AMOUNT = 1000

"""