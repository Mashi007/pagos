"""
Modelo de Conversaciones de WhatsApp para CRM
Almacena conversaciones entre clientes y el bot
"""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class ConversacionWhatsApp(Base):
    """
    Conversación de WhatsApp entre cliente y bot
    """

    __tablename__ = "conversaciones_whatsapp"

    id = Column(Integer, primary_key=True, index=True)

    # Información del mensaje
    message_id = Column(String(100), nullable=True, unique=True, index=True)  # ID de Meta
    from_number = Column(String(20), nullable=False, index=True)  # Número que envía
    to_number = Column(String(20), nullable=False)  # Número que recibe (tu número)
    message_type = Column(String(20), nullable=False)  # text, image, document, etc.
    body = Column(Text, nullable=True)  # Contenido del mensaje
    timestamp = Column(DateTime, nullable=False, index=True)  # Timestamp de Meta

    # Dirección del mensaje
    direccion = Column(String(10), nullable=False)  # INBOUND (cliente -> bot) o OUTBOUND (bot -> cliente)

    # Relación con cliente
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True, index=True)

    # Estado y procesamiento
    procesado = Column(Boolean, default=False, nullable=False)  # Si fue procesado por el bot
    respuesta_enviada = Column(Boolean, default=False, nullable=False)  # Si se envió respuesta
    respuesta_id = Column(Integer, ForeignKey("conversaciones_whatsapp.id"), nullable=True)  # ID de la respuesta

    # Información de respuesta del bot
    respuesta_bot = Column(Text, nullable=True)  # Respuesta generada por el bot
    respuesta_meta_id = Column(String(100), nullable=True)  # ID de mensaje de respuesta en Meta

    # Errores
    error = Column(Text, nullable=True)  # Error al procesar o responder

    # Auditoría
    creado_en = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    actualizado_en = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relaciones ORM
    cliente = relationship("Cliente", foreign_keys=[cliente_id])
    respuesta = relationship("ConversacionWhatsApp", remote_side=[id], foreign_keys=[respuesta_id])

    def __repr__(self):
        return f"<ConversacionWhatsApp {self.id} - {self.direccion} - {self.from_number}>"

    def to_dict(self):
        """Convierte la conversación a diccionario"""
        return {
            "id": self.id,
            "message_id": self.message_id,
            "from_number": self.from_number,
            "to_number": self.to_number,
            "message_type": self.message_type,
            "body": self.body,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "direccion": self.direccion,
            "cliente_id": self.cliente_id,
            "procesado": self.procesado,
            "respuesta_enviada": self.respuesta_enviada,
            "respuesta_id": self.respuesta_id,
            "respuesta_bot": self.respuesta_bot,
            "respuesta_meta_id": self.respuesta_meta_id,
            "error": self.error,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
            "actualizado_en": self.actualizado_en.isoformat() if self.actualizado_en else None,
        }
