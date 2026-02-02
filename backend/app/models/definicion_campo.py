"""
Modelo para catálogo de campos (tablas/campos/definiciones/reglas de negocio).
Usado por Configuración > AI > Catálogo de Campos para sincronizar esquema de BD
y mantener definiciones y notas para entrenamiento AI.
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func

from app.core.database import Base


class DefinicionCampo(Base):
    __tablename__ = "definiciones_campos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tabla = Column(String(200), nullable=False, index=True)
    campo = Column(String(200), nullable=False, index=True)
    definicion = Column(Text, nullable=False)
    tipo_dato = Column(String(100), nullable=True)
    es_obligatorio = Column(Boolean, nullable=False, default=False)
    tiene_indice = Column(Boolean, nullable=False, default=False)
    es_clave_foranea = Column(Boolean, nullable=False, default=False)
    tabla_referenciada = Column(String(200), nullable=True)
    campo_referenciado = Column(String(200), nullable=True)
    # JSON arrays almacenados como texto: ["a","b"]
    valores_posibles = Column(Text, nullable=True)
    ejemplos_valores = Column(Text, nullable=True)
    notas = Column(Text, nullable=True)
    activo = Column(Boolean, nullable=False, default=True)
    orden = Column(Integer, nullable=False, default=0)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
