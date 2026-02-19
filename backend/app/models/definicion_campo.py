"""
Modelo para catálogo de campos (tablas/campos/definiciones/reglas de negocio).
Usado por Configuración > AI > Catálogo de Campos para sincronizar esquema de BD
y mantener definiciones y notas para entrenamiento AI.

Incluye referencias por nombre (string) para backward compatibility y referencias por FK
para integridad referencial (tabla_id, tabla_referenciada_id, campo_referenciado_id).
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class TablaEsquema(Base):
    """Tabla del esquema para referencia FK."""
    __tablename__ = "tablas_esquema"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre_tabla = Column(String(200), nullable=False, unique=True, index=True)
    descripcion = Column(Text, nullable=True)
    activa = Column(Boolean, nullable=False, default=True)
    creada_en = Column(DateTime(timezone=True), server_default=func.now())

    # Relaciones
    definiciones = relationship("DefinicionCampo", back_populates="tabla_rel", foreign_keys="DefinicionCampo.tabla_id")
    referencias = relationship("DefinicionCampo", back_populates="tabla_ref_rel", foreign_keys="DefinicionCampo.tabla_referenciada_id")


class CampoEsquema(Base):
    """Campo del esquema para referencia FK."""
    __tablename__ = "campos_esquema"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tabla_id = Column(Integer, ForeignKey("tablas_esquema.id"), nullable=False, index=True)
    nombre_campo = Column(String(200), nullable=False, index=True)
    tipo_dato = Column(String(100), nullable=True)
    activo = Column(Boolean, nullable=False, default=True)

    # Relaciones
    tabla = relationship("TablaEsquema")
    definiciones = relationship("DefinicionCampo", back_populates="campo_ref_rel")


class DefinicionCampo(Base):
    __tablename__ = "definiciones_campos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Referencias por string (backward compatible)
    tabla = Column(String(200), nullable=False, index=True)
    campo = Column(String(200), nullable=False, index=True)
    tabla_referenciada = Column(String(200), nullable=True, index=True)
    campo_referenciado = Column(String(200), nullable=True)
    
    # Referencias por FK (nueva arquitectura - nullable para backward compat)
    tabla_id = Column(Integer, ForeignKey("tablas_esquema.id"), nullable=True, index=True)
    tabla_referenciada_id = Column(Integer, ForeignKey("tablas_esquema.id"), nullable=True, index=True)
    campo_referenciado_id = Column(Integer, ForeignKey("campos_esquema.id"), nullable=True)
    
    # Definición del campo
    definicion = Column(Text, nullable=False)
    tipo_dato = Column(String(100), nullable=True)
    es_obligatorio = Column(Boolean, nullable=False, default=False)
    tiene_indice = Column(Boolean, nullable=False, default=False)
    es_clave_foranea = Column(Boolean, nullable=False, default=False)
    
    # JSON arrays almacenados como texto: ["a","b"]
    valores_posibles = Column(Text, nullable=True)
    ejemplos_valores = Column(Text, nullable=True)
    notas = Column(Text, nullable=True)
    
    activo = Column(Boolean, nullable=False, default=True)
    orden = Column(Integer, nullable=False, default=0)
    creado_en = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    actualizado_en = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relaciones
    tabla_rel = relationship("TablaEsquema", back_populates="definiciones", foreign_keys=[tabla_id])
    tabla_ref_rel = relationship("TablaEsquema", back_populates="referencias", foreign_keys=[tabla_referenciada_id])
    campo_ref_rel = relationship("CampoEsquema", back_populates="definiciones")
