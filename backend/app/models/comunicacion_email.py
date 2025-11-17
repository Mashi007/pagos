"""
Modelo de Comunicaciones de Email para CRM
Almacena emails recibidos y enviados vinculados con clientes
"""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class ComunicacionEmail(Base):
    """
    Comunicación de Email entre cliente y sistema
    """

    __tablename__ = "comunicaciones_email"

    id = Column(Integer, primary_key=True, index=True)

    # Información del email
    message_id = Column(String(200), nullable=True, unique=True, index=True)  # ID del email
    from_email = Column(String(200), nullable=False, index=True)  # Email que envía
    to_email = Column(String(200), nullable=False, index=True)  # Email que recibe
    subject = Column(String(500), nullable=True)  # Asunto del email
    body = Column(Text, nullable=True)  # Contenido del email
    body_html = Column(Text, nullable=True)  # Contenido HTML del email
    timestamp = Column(DateTime, nullable=False, index=True)  # Timestamp del email

    # Dirección del mensaje
    direccion = Column(String(10), nullable=False)  # INBOUND (cliente -> sistema) o OUTBOUND (sistema -> cliente)

    # Relación con cliente
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True, index=True)

    # Relación con ticket (opcional)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True, index=True)

    # Estado y procesamiento
    procesado = Column(Boolean, default=False, nullable=False)  # Si fue procesado
    respuesta_enviada = Column(Boolean, default=False, nullable=False)  # Si se envió respuesta
    respuesta_id = Column(Integer, ForeignKey("comunicaciones_email.id"), nullable=True)  # ID de la respuesta
    requiere_respuesta = Column(Boolean, default=False, nullable=False, index=True)  # Si requiere respuesta manual

    # Información de respuesta
    respuesta_automatica = Column(Text, nullable=True)  # Respuesta generada automáticamente
    respuesta_enviada_id = Column(String(200), nullable=True)  # ID del email de respuesta enviado

    # Errores
    error = Column(Text, nullable=True)  # Error al procesar o responder

    # Adjuntos (JSON con información de archivos adjuntos)
    adjuntos = Column(Text, nullable=True)  # JSON string con lista de adjuntos

    # Auditoría
    creado_en = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    actualizado_en = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relaciones ORM
    cliente = relationship("Cliente", foreign_keys=[cliente_id])
    respuesta = relationship("ComunicacionEmail", remote_side=[id], foreign_keys=[respuesta_id])
    ticket = relationship(
        "Ticket", foreign_keys=[ticket_id], uselist=False, primaryjoin="ComunicacionEmail.ticket_id == Ticket.id"
    )
    tickets = relationship("Ticket", foreign_keys="Ticket.comunicacion_email_id", back_populates="comunicacion_email")

    def __repr__(self):
        return f"<ComunicacionEmail {self.id} - {self.direccion} - {self.from_email}>"

    def to_dict(self):
        """Convierte la comunicación a diccionario"""
        return {
            "id": self.id,
            "message_id": self.message_id,
            "from_email": self.from_email,
            "to_email": self.to_email,
            "subject": self.subject,
            "body": self.body,
            "body_html": self.body_html,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "direccion": self.direccion,
            "cliente_id": self.cliente_id,
            "ticket_id": self.ticket_id,
            "procesado": self.procesado,
            "respuesta_enviada": self.respuesta_enviada,
            "respuesta_id": self.respuesta_id,
            "requiere_respuesta": self.requiere_respuesta,
            "respuesta_automatica": self.respuesta_automatica,
            "respuesta_enviada_id": self.respuesta_enviada_id,
            "error": self.error,
            "adjuntos": self.adjuntos,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
            "actualizado_en": self.actualizado_en.isoformat() if self.actualizado_en else None,
        }
