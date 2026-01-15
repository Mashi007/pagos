"""
Modelo de Definiciones de Campos para AI
Almacena definiciones de campos de BD para entrenar acceso rápido
"""

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.db.session import Base


class AIDefinicionCampo(Base):
    """
    Definiciones de campos de BD para entrenar acceso rápido
    """

    __tablename__ = "ai_definiciones_campos"

    id = Column(Integer, primary_key=True, index=True)
    tabla = Column(String(100), nullable=False, index=True)  # Nombre de la tabla (ej: "clientes")
    campo = Column(String(100), nullable=False, index=True)  # Nombre del campo (ej: "cedula")
    definicion = Column(Text, nullable=False)  # Definición del campo
    tipo_dato = Column(String(50), nullable=True)  # Tipo de dato (ej: "VARCHAR", "INTEGER", "DATE")
    es_obligatorio = Column(Boolean, nullable=False, default=False)  # Si es NOT NULL
    tiene_indice = Column(Boolean, nullable=False, default=False)  # Si tiene índice
    es_clave_foranea = Column(Boolean, nullable=False, default=False)  # Si es FK
    tabla_referenciada = Column(String(100), nullable=True)  # Tabla referenciada si es FK
    campo_referenciado = Column(String(100), nullable=True)  # Campo referenciado si es FK
    valores_posibles = Column(Text, nullable=True)  # JSON: ["valor1", "valor2"] - valores posibles (ej: estados)
    ejemplos_valores = Column(Text, nullable=True)  # JSON: ["ejemplo1", "ejemplo2"] - ejemplos de valores
    notas = Column(Text, nullable=True)  # Notas adicionales sobre el campo
    activo = Column(Boolean, nullable=False, default=True, index=True)  # Si está activo o no
    orden = Column(Integer, nullable=True, default=0)  # Orden de visualización

    # Auditoría
    creado_en = Column(DateTime, server_default=func.now(), nullable=False)
    actualizado_en = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<AIDefinicionCampo {self.tabla}.{self.campo}: {self.definicion[:50]}>"

    def to_dict(self):
        """Convierte la definición a diccionario Python"""
        import json
        
        return {
            "id": self.id,
            "tabla": self.tabla,
            "campo": self.campo,
            "definicion": self.definicion,
            "tipo_dato": self.tipo_dato,
            "es_obligatorio": self.es_obligatorio,
            "tiene_indice": self.tiene_indice,
            "es_clave_foranea": self.es_clave_foranea,
            "tabla_referenciada": self.tabla_referenciada,
            "campo_referenciado": self.campo_referenciado,
            "valores_posibles": json.loads(self.valores_posibles) if self.valores_posibles else [],
            "ejemplos_valores": json.loads(self.ejemplos_valores) if self.ejemplos_valores else [],
            "notas": self.notas,
            "activo": self.activo,
            "orden": self.orden,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
            "actualizado_en": self.actualizado_en.isoformat() if self.actualizado_en else None,
        }
