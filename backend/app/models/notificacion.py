"""
Modelo de Notificación
Actualizado para coincidir con la estructura real de la base de datos
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, JSON
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
    ✅ ACTUALIZADO: Sincronizado con estructura real de la BD
    """

    __tablename__ = "notificaciones"

    id = Column(Integer, primary_key=True, index=True)

    # Destinatario
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    # ✅ NUEVO: Información de destinatario (existe en BD)
    destinatario_email = Column(String(255), nullable=True)
    destinatario_telefono = Column(String(20), nullable=True)
    destinatario_nombre = Column(String(255), nullable=True)

    # Contenido
    tipo = Column(String(20), nullable=False, index=True)  # EMAIL, SMS, WHATSAPP (USER-DEFINED enum en BD)
    categoria = Column(String(50), nullable=False, default="GENERAL", index=True)  # ✅ NUEVO: Existe en BD como USER-DEFINED enum
    asunto = Column(String(255), nullable=True)
    mensaje = Column(Text, nullable=False)
    extra_data = Column(JSON, nullable=True)  # ✅ NUEVO: Existe en BD

    # Estado y control
    estado = Column(String(20), nullable=False, default="PENDIENTE", index=True)  # USER-DEFINED enum en BD
    prioridad = Column(String(20), nullable=False, default="MEDIA", index=True)  # ✅ NUEVO: Existe en BD como USER-DEFINED enum
    programada_para = Column(DateTime(timezone=True), nullable=True, index=True)
    enviada_en = Column(DateTime(timezone=True), nullable=True)
    # ✅ CORREGIDO: leida -> leida_en (timestamp en lugar de boolean)
    leida_en = Column(DateTime(timezone=True), nullable=True)

    # Reintentos y errores
    intentos = Column(Integer, nullable=True)  # ✅ CORREGIDO: nullable=True (como en BD)
    max_intentos = Column(Integer, nullable=True)  # ✅ NUEVO: Existe en BD
    respuesta_servicio = Column(Text, nullable=True)
    error_mensaje = Column(Text, nullable=True)

    # Timestamps
    # ✅ CORREGIDO: created_at -> creado_en (nombre en BD)
    creado_en = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    actualizado_en = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

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
        return str(self.estado) == EstadoNotificacion.FALLIDA.value and self.intentos < 3

    def marcar_enviada(self, respuesta: Optional[str] = None):
        """Marca la notificación como enviada"""
        self.estado = EstadoNotificacion.ENVIADA.value  # type: ignore[assignment]
        self.respuesta_servicio = respuesta  # type: ignore[assignment]
        self.enviada_en = datetime.utcnow()  # type: ignore[assignment]

    def marcar_fallida(self, error: str):
        """Marca la notificación como fallida"""
        self.estado = EstadoNotificacion.FALLIDA.value  # type: ignore[assignment]
        self.error_mensaje = error  # type: ignore[assignment]
        self.intentos += 1

    def marcar_leida(self):
        """Marca la notificación como leída"""
        if str(self.estado) == EstadoNotificacion.ENVIADA.value:
            self.leida_en = datetime.utcnow()  # ✅ CORREGIDO: Usar leida_en (timestamp)

    # Propiedades de compatibilidad para esquemas de respuesta
    @property
    def fecha_envio(self):
        return self.enviada_en

    @property
    def fecha_creacion(self):
        return self.creado_en  # ✅ CORREGIDO: Usar creado_en
    
    # ✅ NUEVO: Propiedad de compatibilidad para leida (boolean basado en leida_en)
    @property
    def leida(self) -> bool:
        """Indica si la notificación fue leída (basado en leida_en)"""
        return self.leida_en is not None
    
    # ✅ NUEVO: Propiedad de compatibilidad para created_at
    @property
    def created_at(self):
        """Compatibilidad: alias para creado_en"""
        return self.creado_en
    
    # ✅ NUEVO: Propiedad de compatibilidad para canal (calculada desde tipo)
    @property
    def canal(self) -> Optional[str]:
        """
        Compatibilidad: canal calculado desde tipo
        El campo 'canal' no existe en BD, pero se usa en el código.
        Se calcula desde 'tipo' para mantener compatibilidad.
        """
        if self.tipo in ["EMAIL", "WHATSAPP", "SMS", "PUSH"]:
            return self.tipo
        return None
    
    @canal.setter
    def canal(self, value: Optional[str]):
        """
        Setter para canal: actualiza tipo si es necesario
        """
        if value and value in ["EMAIL", "WHATSAPP", "SMS", "PUSH"]:
            self.tipo = value

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
            "destinatario_email": self.destinatario_email,
            "destinatario_telefono": self.destinatario_telefono,
            "destinatario_nombre": self.destinatario_nombre,
            "tipo": self.tipo,
            "categoria": self.categoria,
            "asunto": self.asunto,
            "mensaje": self.mensaje,
            "estado": self.estado,
            "prioridad": self.prioridad,
            "programada_para": (self.programada_para.isoformat() if self.programada_para else None),
            "enviada_en": self.enviada_en.isoformat() if self.enviada_en else None,
            "leida_en": self.leida_en.isoformat() if self.leida_en else None,
            "leida": self.leida,  # Propiedad calculada basada en leida_en
            "intentos": self.intentos,
            "max_intentos": self.max_intentos,
            "respuesta_servicio": self.respuesta_servicio,
            "error_mensaje": self.error_mensaje,
            "extra_data": self.extra_data,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
            "actualizado_en": self.actualizado_en.isoformat() if self.actualizado_en else None,
            # Compatibilidad con código existente
            "created_at": self.creado_en.isoformat() if self.creado_en else None,
        }
