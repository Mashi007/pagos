"""
Modelo para conversaciones de entrenamiento AI (fine-tuning).
Usado por Configuración > AI > Fine-tuning para listar, crear, calificar y preparar datos.
"""
from sqlalchemy import Column, Integer, String, Text, Float, DateTime
from sqlalchemy.sql import func

from app.core.database import Base


class ConversacionAI(Base):
    __tablename__ = "conversaciones_ai"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    pregunta = Column(Text, nullable=False)
    respuesta = Column(Text, nullable=False)
    contexto_usado = Column(Text, nullable=True)
    documentos_usados = Column(Text, nullable=True)  # JSON array [1,2,3]
    modelo_usado = Column(String(100), nullable=True)
    tokens_usados = Column(Integer, nullable=True)
    tiempo_respuesta = Column(Integer, nullable=True)  # ms
    calificacion = Column(Integer, nullable=True)  # 1-5
    feedback = Column(Text, nullable=True)
    usuario_id = Column(Integer, nullable=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
