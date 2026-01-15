"""
Modelo de Calificaciones del Chat AI
Almacena las calificaciones (pulgar arriba/abajo) de las respuestas del AI
"""

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.db.session import Base


class AICalificacionChat(Base):
    """
    Calificaciones de respuestas del Chat AI
    """

    __tablename__ = "ai_calificaciones_chat"

    id = Column(Integer, primary_key=True, index=True)
    pregunta = Column(Text, nullable=False)  # Pregunta del usuario
    respuesta_ai = Column(Text, nullable=False)  # Respuesta del AI
    calificacion = Column(String(20), nullable=False, index=True)  # "arriba" o "abajo"
    usuario_email = Column(String(255), nullable=True, index=True)  # Email del usuario que calificó
    procesado = Column(Boolean, nullable=False, default=False, index=True)  # Si ya se procesó para mejorar
    notas_procesamiento = Column(Text, nullable=True)  # Notas sobre cómo se procesó
    mejorado = Column(Boolean, nullable=False, default=False)  # Si se mejoró el sistema basado en esto

    # Auditoría
    creado_en = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    actualizado_en = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<AICalificacionChat {self.calificacion}: {self.pregunta[:50]}>"

    def to_dict(self):
        """Convierte la calificación a diccionario Python"""
        return {
            "id": self.id,
            "pregunta": self.pregunta,
            "respuesta_ai": self.respuesta_ai,
            "calificacion": self.calificacion,
            "usuario_email": self.usuario_email,
            "procesado": self.procesado,
            "notas_procesamiento": self.notas_procesamiento,
            "mejorado": self.mejorado,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
            "actualizado_en": self.actualizado_en.isoformat() if self.actualizado_en else None,
        }
