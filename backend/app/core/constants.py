# backend/app/core/constants.py
from enum import Enum


class Roles(str, Enum):
    """Roles de usuario en el sistema"""
    ADMIN = "ADMIN"
    COBRANZAS = "COBRANZAS"
    ASESOR = "ASESOR"
    VALIDADOR = "VALIDADOR"
    SOLO_LECTURA = "SOLO_LECTURA"


class EstadoUsuario(str, Enum):
    """Estados de usuario"""
    ACTIVO = "ACTIVO"
    INACTIVO = "INACTIVO"
    BLOQUEADO = "BLOQUEADO"
    SUSPENDIDO = "SUSPENDIDO"


class TipoNotificacion(str, Enum):
    """Tipos de notificación"""
    EMAIL = "EMAIL"
    SMS = "SMS"
    WHATSAPP = "WHATSAPP"
    PUSH = "PUSH"
    SISTEMA = "SISTEMA"


class EstadoNotificacion(str, Enum):
    """Estados de notificación"""
    PENDIENTE = "PENDIENTE"
    ENVIADA = "ENVIADA"
    FALLIDA = "FALLIDA"
    LEIDA = "LEIDA"


class EstadoAprobacion(str, Enum):
    """Estados de aprobación"""
    PENDIENTE = "PENDIENTE"
    APROBADA = "APROBADA"
    RECHAZADA = "RECHAZADA"
    CANCELADA = "CANCELADA"


class TipoMovimiento(str, Enum):
    """Tipos de movimiento en auditoría"""
    CREACION = "CREACION"
    ACTUALIZACION = "ACTUALIZACION"
    ELIMINACION = "ELIMINACION"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    CAMBIO_PASSWORD = "CAMBIO_PASSWORD"
    APROBACION = "APROBACION"
    RECHAZO = "RECHAZO"


class MetodoPago(str, Enum):
    """Métodos de pago"""
    EFECTIVO = "EFECTIVO"
    TRANSFERENCIA = "TRANSFERENCIA"
    DEPOSITO = "DEPOSITO"
    CHEQUE = "CHEQUE"
    TARJETA = "TARJETA"


class EstadoPago(str, Enum):
    """Estados de pago"""
    PENDIENTE = "PENDIENTE"
    PAGADO = "PAGADO"
    PARCIAL = "PARCIAL"
    VENCIDO = "VENCIDO"
    ANULADO = "ANULADO"


# Permisos por rol
PERMISOS_POR_ROL = {
    Roles.ADMIN: [
        "clientes.*",
        "prestamos.*",
        "pagos.*",
        "usuarios.*",
        "configuracion.*",
        "reportes.*",
        "aprobaciones.*",
    ],
    Roles.COBRANZAS: [
        "clientes.read",
        "prestamos.read",
        "pagos.*",
        "reportes.cobranza",
        "notificaciones.enviar",
    ],
    Roles.ASESOR: [
        "clientes.*",
        "prestamos.create",
        "prestamos.read",
        "prestamos.update",
        "pagos.read",
        "reportes.basicos",
    ],
    Roles.VALIDADOR: [
        "clientes.read",
        "prestamos.read",
        "prestamos.aprobar",
        "pagos.read",
        "aprobaciones.*",
    ],
    Roles.SOLO_LECTURA: [
        "clientes.read",
        "prestamos.read",
        "pagos.read",
        "reportes.basicos",
    ],
}
