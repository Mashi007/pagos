# backend/app/models/notificacion.py
"""
Modelo de Notificación
Sistema de notificaciones por email, SMS o WhatsApp
"""

from enum import Enum as PyEnum
# from sqlalchemy import  # TODO: Agregar imports específicos
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base


# Enums para mejor validación y tipado


class EstadoNotificacion(str, PyEnum):
    PENDIENTE = "PENDIENTE"
    ENVIADA = "ENVIADA"
    FALLIDA = "FALLIDA"
    LEIDA = "LEIDA"


class TipoNotificacion(str, PyEnum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    WHATSAPP = "WHATSAPP"
    PUSH = "PUSH"


class CategoriaNotificacion(str, PyEnum):
    """Categorías de notificación"""
    RECORDATORIO_PAGO = "RECORDATORIO_PAGO"
    PRESTAMO_APROBADO = "PRESTAMO_APROBADO"
    PRESTAMO_RECHAZADO = "PRESTAMO_RECHAZADO"
    CUOTA_VENCIDA = "CUOTA_VENCIDA"
    CUOTA_PROXIMA = "CUOTA_PROXIMA"
    PAGO_RECIBIDO = "PAGO_RECIBIDO"
    MORA_APLICADA = "MORA_APLICADA"
    GENERAL = "GENERAL"


class PrioridadNotificacion(str, PyEnum):
    """Niveles de prioridad"""
    BAJA = "BAJA"
    NORMAL = "NORMAL"
    ALTA = "ALTA"
    URGENTE = "URGENTE"


class Notificacion(Base):
    """
    """"""
    __tablename__ = "notificaciones"

    # Identificación
    id = Column(Integer, primary_key=True, index=True)

    # Destinatario (puede ser un User o un Cliente por email/teléfono)
    user_id = Column
    cliente_id = Column
        ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=True,
        index=True,

    # Destinatario manual (si no es user ni cliente registrado)
    destinatario_email = Column(String(255), nullable=True)
    destinatario_telefono = Column(String(20), nullable=True)
    destinatario_nombre = Column(String(255), nullable=True)

    # Tipo de notificación
    tipo = Column(Enum(TipoNotificacion), nullable=False, index=True)

    # Categoría
    categoria = Column
        Enum(CategoriaNotificacion),
        nullable=False,
        default=CategoriaNotificacion.GENERAL,
        index=True,

    # Contenido
    asunto = Column(String(255), nullable=True)
    mensaje = Column(Text, nullable=False)

    # evitar conflicto con SQLAlchemy
    extra_data = Column(JSON, nullable=True)

    # Estado de envío
    estado = Column
        Enum(EstadoNotificacion),
        nullable=False,
        default=EstadoNotificacion.PENDIENTE,
        index=True,


    # Fechas
    programada_para = Column
    )  # Para notificaciones programadas

    # Respuesta del servicio de envío
    respuesta_servicio = Column(Text, nullable=True)
    error_mensaje = Column(Text, nullable=True)

    # Prioridad
    prioridad = Column
        Enum(PrioridadNotificacion),
        nullable=False,
        default=PrioridadNotificacion.NORMAL,

    # Auditoría

    # Relaciones
    user = relationship("User", back_populates="notificaciones")
    # cliente = relationship("Cliente", back_populates="notificaciones")  # COMENTADO: Tabla notificaciones vacía


    def __repr__(self):
        return 

    @property
    def esta_pendiente(self) -> bool:
        """Verifica si la notificación está pendiente"""
        return self.estado == EstadoNotificacion.PENDIENTE

    @property
    def fue_enviada(self) -> bool:
        """Verifica si la notificación fue enviada"""
        return self.estado == EstadoNotificacion.ENVIADA

    @property
    def fallo(self) -> bool:
        """Verifica si la notificación falló"""
        return self.estado == EstadoNotificacion.FALLIDA

    @property
    def puede_reintentar(self) -> bool:
        """Verifica si se puede reintentar el envío"""


    def marcar_enviada(self, respuesta: str = None):
        """Marca la notificación como enviada"""
        self.estado = EstadoNotificacion.ENVIADA
        self.respuesta_servicio = respuesta


    def marcar_fallida(self, error: str):
        """Marca la notificación como fallida"""
        self.estado = EstadoNotificacion.FALLIDA
        self.error_mensaje = error


    def marcar_leida(self):
        """Marca la notificación como leída"""
        if self.estado == EstadoNotificacion.ENVIADA:

    @classmethod
    def crear_recordatorio_pago
        """"""
        Helper para crear notificaciones de recordatorio de pago

        Args:
            cliente_id: ID del cliente
            tipo: TipoNotificacion (EMAIL, SMS o WHATSAPP)
            mensaje: Mensaje de la notificación
            programada_para: Fecha/hora programada (opcional)

        Returns:
            Notificacion: Instancia de notificación
        """"""
        return cls

"""
""""""