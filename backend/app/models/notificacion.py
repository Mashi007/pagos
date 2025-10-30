"""
Modelo de Notificación
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class TipoNotificacion(str, Enum):
    """Tipos de notificación disponibles"""

    EMAIL = "EMAIL"
    SMS = "SMS"
    WHATSAPP = "WHATSAPP"
    PUSH = "PUSH"


class EstadoNotificacion(str, Enum):
    """Estados posibles de una notificación"""

    PENDIENTE = "PENDIENTE"
    ENVIADA = "ENVIADA"
    FALLIDA = "FALLIDA"
    CANCELADA = "CANCELADA"


class Notificacion(Base):
    """
    Modelo para notificaciones del sistema
    Maneja el envío de notificaciones por diferentes canales
    """

    __tablename__ = "notificaciones"

    id = Column(Integer, primary_key=True, index=True)

    # Destinatario
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # Contenido
    tipo = Column(String(20), nullable=False, index=True)  # EMAIL, SMS, WHATSAPP
    canal = Column(String(20), nullable=True, index=True)
    asunto = Column(String(255), nullable=True)
    mensaje = Column(Text, nullable=False)

    # Estado y control
    estado = Column(String(20), nullable=False, default="PENDIENTE", index=True)
    programada_para = Column(DateTime, nullable=True, index=True)
    enviada_en = Column(DateTime, nullable=True)
    leida = Column(Boolean, default=False, nullable=False)

    # Reintentos y errores
    intentos = Column(Integer, default=0, nullable=False)
    respuesta_servicio = Column(Text, nullable=True)
    error_mensaje = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relaciones
    user = relationship("User", back_populates="notificaciones")

    def __repr__(self):
        return f"<Notificacion(id={self.id}, tipo={self.tipo}, estado={self.estado})>"

    @property
    def esta_pendiente(self) -> bool:
        """Verifica si la notificación está pendiente"""
        return str(self.estado) == EstadoNotificacion.PENDIENTE.value

    @property
    def fue_enviada(self) -> bool:
        """Verifica si la notificación fue enviada"""
        return str(self.estado) == EstadoNotificacion.ENVIADA.value

    @property
    def fallo(self) -> bool:
        """Verifica si la notificación falló"""
        return str(self.estado) == EstadoNotificacion.FALLIDA.value

    @property
    def puede_reintentar(self) -> bool:
        """Verifica si se puede reintentar el envío"""
        return (
            str(self.estado) == EstadoNotificacion.FALLIDA.value and self.intentos < 3
        )

    def marcar_enviada(self, respuesta: str = None):
        """Marca la notificación como enviada"""
        self.estado = EstadoNotificacion.ENVIADA.value
        self.respuesta_servicio = respuesta
        self.enviada_en = datetime.utcnow()

    def marcar_fallida(self, error: str):
        """Marca la notificación como fallida"""
        self.estado = EstadoNotificacion.FALLIDA.value
        self.error_mensaje = error
        self.intentos += 1

    def marcar_leida(self):
        """Marca la notificación como leída"""
        if str(self.estado) == EstadoNotificacion.ENVIADA.value:
            self.leida = True

    # Propiedades de compatibilidad para esquemas de respuesta
    @property
    def fecha_envio(self):
        return self.enviada_en

    @property
    def fecha_creacion(self):
        return self.created_at

    @classmethod
    def crear_recordatorio_pago(
        cls,
        cliente_id: int,
        tipo: str,
        mensaje: str,
        programada_para: Optional[datetime] = None,
    ):
        """
        Helper para crear notificaciones de recordatorio de pago

        Args:
            cliente_id: ID del cliente
            tipo: TipoNotificacion (EMAIL, SMS o WHATSAPP)
            mensaje: Mensaje de la notificación
            programada_para: Fecha/hora programada (opcional)

        Returns:
            Notificacion: Instancia de notificación
        """
        return cls(
            cliente_id=cliente_id,
            tipo=tipo,
            mensaje=mensaje,
            programada_para=programada_para or datetime.utcnow(),
        )

    def to_dict(self):
        """Convierte la notificación a diccionario"""
        return {
            "id": self.id,
            "cliente_id": self.cliente_id,
            "user_id": self.user_id,
            "tipo": self.tipo,
            "mensaje": self.mensaje,
            "estado": self.estado,
            "programada_para": (
                self.programada_para.isoformat() if self.programada_para else None
            ),
            "enviada_en": self.enviada_en.isoformat() if self.enviada_en else None,
            "leida": self.leida,
            "intentos": self.intentos,
            "respuesta_servicio": self.respuesta_servicio,
            "error_mensaje": self.error_mensaje,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
