"""
Modelo de Variable de Prompt AI
Almacena variables personalizadas que se pueden usar en los prompts del AI
"""

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.db.session import Base


class AIPromptVariable(Base):
    """
    Variable personalizada para prompts del AI
    """

    __tablename__ = "ai_prompt_variables"

    id = Column(Integer, primary_key=True, index=True)
    variable = Column(String(100), nullable=False, unique=True, index=True)  # Nombre de la variable (ej: {mi_variable})
    descripcion = Column(Text, nullable=False)  # Descripción de qué contiene la variable
    activo = Column(Boolean, nullable=False, default=True, index=True)  # Si está activa o no
    orden = Column(Integer, nullable=True, default=0)  # Orden de visualización

    # Auditoría
    creado_en = Column(DateTime, server_default=func.now(), nullable=False)
    actualizado_en = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<AIPromptVariable {self.variable}: {self.descripcion[:50]}>"

    def to_dict(self):
        """Convierte la variable a diccionario"""
        return {
            "id": self.id,
            "variable": self.variable,
            "descripcion": self.descripcion,
            "activo": self.activo,
            "orden": self.orden,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
            "actualizado_en": self.actualizado_en.isoformat() if self.actualizado_en else None,
        }

