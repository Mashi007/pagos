# backend/app/core/constants.py
from enum import Enum


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


# Configuraciones por defecto
DEFAULT_INTEREST_RATE = 0.02  # 2% mensual
DEFAULT_GRACE_DAYS = 3
MAX_LOAN_AMOUNT = 50000
MIN_LOAN_AMOUNT = 1000
