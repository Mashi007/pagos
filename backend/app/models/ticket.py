"""
Modelo de Ticket de Atención
Almacena tickets de atención al cliente vinculados con conversaciones de WhatsApp
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class Ticket(Base):
    """
    Ticket de atención al cliente
    Puede estar vinculado a una conversación de WhatsApp
    """

    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)

    # Información básica
    titulo = Column(String(200), nullable=False, index=True)
    descripcion = Column(Text, nullable=False)

    # Relación con cliente
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True, index=True)

    # Relación con conversación de WhatsApp (opcional)
    conversacion_whatsapp_id = Column(Integer, ForeignKey("conversaciones_whatsapp.id"), nullable=True, index=True)
    
    # Relación con comunicación de Email (opcional)
    comunicacion_email_id = Column(Integer, ForeignKey("comunicaciones_email.id"), nullable=True, index=True)

    # Estado y prioridad
    estado = Column(String(20), nullable=False, default="abierto", index=True)  # abierto, en_proceso, resuelto, cerrado
    prioridad = Column(String(20), nullable=False, default="media", index=True)  # baja, media, urgente
    tipo = Column(String(20), nullable=False, default="consulta", index=True)  # consulta, incidencia, solicitud, reclamo

    # Asignación
    asignado_a = Column(String(200), nullable=True)  # Nombre del usuario asignado
    asignado_a_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # ID del usuario asignado
    
    # Escalación
    escalado_a_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # ID del usuario al que se escaló (admin)
    escalado = Column(Boolean, default=False, nullable=False)  # Si fue escalado a un superior

    # Fecha límite (para agenda)
    fecha_limite = Column(DateTime, nullable=True, index=True)  # Fecha límite para resolución

    # Archivos adjuntos (JSON con rutas de archivos)
    archivos = Column(Text, nullable=True)  # JSON array con rutas de archivos adjuntos

    # Usuario que creó el ticket
    creado_por_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # Auditoría
    creado_en = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    actualizado_en = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relaciones ORM
    cliente = relationship("Cliente", foreign_keys=[cliente_id])
    conversacion_whatsapp = relationship(
        "ConversacionWhatsApp", foreign_keys=[conversacion_whatsapp_id], back_populates="tickets"
    )
    comunicacion_email = relationship(
        "ComunicacionEmail", foreign_keys=[comunicacion_email_id], back_populates="tickets"
    )
    asignado_a_usuario = relationship("User", foreign_keys=[asignado_a_id])
    escalado_a_usuario = relationship("User", foreign_keys=[escalado_a_id])
    creado_por = relationship("User", foreign_keys=[creado_por_id])

    def __repr__(self):
        return f"<Ticket {self.id} - {self.titulo} - {self.estado}>"

    def to_dict(self):
        """Convierte el ticket a diccionario"""
        return {
            "id": self.id,
            "titulo": self.titulo,
            "descripcion": self.descripcion,
            "cliente_id": self.cliente_id,
            "cliente": self.cliente.nombres + " " + self.cliente.apellidos if self.cliente else None,
            "clienteData": (
                {
                    "id": self.cliente.id,
                    "nombres": self.cliente.nombres,
                    "apellidos": self.cliente.apellidos,
                    "cedula": self.cliente.cedula,
                    "telefono": self.cliente.telefono,
                    "email": self.cliente.email,
                }
                if self.cliente
                else None
            ),
            "conversacion_whatsapp_id": self.conversacion_whatsapp_id,
            "comunicacion_email_id": self.comunicacion_email_id,
            "estado": self.estado,
            "prioridad": self.prioridad,
            "tipo": self.tipo,
            "asignado_a": self.asignado_a,
            "asignado_a_id": self.asignado_a_id,
            "escalado_a_id": self.escalado_a_id,
            "escalado": self.escalado,
            "fecha_limite": self.fecha_limite.isoformat() if self.fecha_limite else None,
            "archivos": self.archivos,
            "creado_por_id": self.creado_por_id,
            "fechaCreacion": self.creado_en.isoformat() if self.creado_en else None,
            "fechaActualizacion": self.actualizado_en.isoformat() if self.actualizado_en else None,
        }
