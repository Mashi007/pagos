"""
Modelo para diccionario semántico (Configuración > AI > Diccionario semántico).
Palabras, definiciones, categorías y relación con tablas/campos para entrenamiento AI.
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func

from app.core.database import Base


class DiccionarioSemantico(Base):
    __tablename__ = "diccionario_semantico"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    palabra = Column(String(200), nullable=False, index=True)
    definicion = Column(Text, nullable=False)
    categoria = Column(String(100), nullable=True, index=True)
    campo_relacionado = Column(String(200), nullable=True)
    tabla_relacionada = Column(String(200), nullable=True)
    sinonimos = Column(Text, nullable=True)  # JSON array
    ejemplos_uso = Column(Text, nullable=True)  # JSON array
    activo = Column(Boolean, nullable=False, default=True)
    orden = Column(Integer, nullable=False, default=0)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
