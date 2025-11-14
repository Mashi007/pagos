"""
Modelo de Conversación AI
Almacena conversaciones para fine-tuning
"""

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class ConversacionAI(Base):
    """
    Conversación para entrenamiento de fine-tuning
    """

    __tablename__ = "conversaciones_ai"

    id = Column(Integer, primary_key=True, index=True)
    
    # Contenido de la conversación
    pregunta = Column(Text, nullable=False)
    respuesta = Column(Text, nullable=False)
    contexto_usado = Column(Text, nullable=True)
    
    # Documentos usados (IDs separados por coma)
    documentos_usados = Column(String(500), nullable=True)
    
    # Información del modelo
    modelo_usado = Column(String(100), nullable=True)
    tokens_usados = Column(Integer, nullable=True)
    tiempo_respuesta = Column(Integer, nullable=True)  # en milisegundos
    
    # Calificación para fine-tuning
    calificacion = Column(Integer, nullable=True)  # 1-5 estrellas
    feedback = Column(Text, nullable=True)
    
    # Usuario que generó la conversación
    usuario_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Relaciones opcionales con tablas base del sistema
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True, index=True)
    prestamo_id = Column(Integer, ForeignKey("prestamos.id"), nullable=True, index=True)
    pago_id = Column(Integer, ForeignKey("pagos.id"), nullable=True, index=True)
    cuota_id = Column(Integer, ForeignKey("cuotas.id"), nullable=True, index=True)
    
    # Auditoría
    creado_en = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    actualizado_en = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relaciones ORM
    usuario = relationship("User", foreign_keys=[usuario_id])
    cliente = relationship("Cliente", foreign_keys=[cliente_id])
    prestamo = relationship("Prestamo", foreign_keys=[prestamo_id])
    pago = relationship("Pago", foreign_keys=[pago_id])
    cuota = relationship("Cuota", foreign_keys=[cuota_id])
    
    def __repr__(self):
        return f"<ConversacionAI {self.id} - {self.pregunta[:50]}...>"
    
    def to_dict(self):
        """Convierte la conversación a diccionario"""
        return {
            "id": self.id,
            "pregunta": self.pregunta,
            "respuesta": self.respuesta,
            "contexto_usado": self.contexto_usado,
            "documentos_usados": self.documentos_usados.split(",") if self.documentos_usados else [],
            "modelo_usado": self.modelo_usado,
            "tokens_usados": self.tokens_usados,
            "tiempo_respuesta": self.tiempo_respuesta,
            "calificacion": self.calificacion,
            "feedback": self.feedback,
            "usuario_id": self.usuario_id,
            "cliente_id": self.cliente_id,
            "prestamo_id": self.prestamo_id,
            "pago_id": self.pago_id,
            "cuota_id": self.cuota_id,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
            "actualizado_en": self.actualizado_en.isoformat() if self.actualizado_en else None,
        }

