"""
Modelo de Diccionario Semántico para AI
Almacena palabras y sus definiciones para mejorar la comprensión del AI
"""

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.db.session import Base


class AIDiccionarioSemantico(Base):
    """
    Diccionario semántico: palabras con definiciones para entrenar al AI
    """

    __tablename__ = "ai_diccionario_semantico"

    id = Column(Integer, primary_key=True, index=True)
    palabra = Column(String(200), nullable=False, unique=True, index=True)  # Palabra o término
    definicion = Column(Text, nullable=False)  # Definición de la palabra
    categoria = Column(String(100), nullable=True, index=True)  # Ej: "identificacion", "pagos", "prestamos"
    campo_relacionado = Column(String(100), nullable=True)  # Campo técnico relacionado (ej: "cedula", "nombres")
    tabla_relacionada = Column(String(100), nullable=True)  # Tabla relacionada (ej: "clientes", "pagos")
    sinonimos = Column(Text, nullable=True)  # JSON: ["sinónimo1", "sinónimo2"] - palabras similares
    ejemplos_uso = Column(Text, nullable=True)  # JSON: ["ejemplo1", "ejemplo2"] - ejemplos de uso
    activo = Column(Boolean, nullable=False, default=True, index=True)  # Si está activo o no
    orden = Column(Integer, nullable=True, default=0)  # Orden de visualización

    # Auditoría
    creado_en = Column(DateTime, server_default=func.now(), nullable=False)
    actualizado_en = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<AIDiccionarioSemantico {self.palabra}: {self.definicion[:50]}>"

    def to_dict(self):
        """Convierte el diccionario a diccionario Python"""
        import json
        
        return {
            "id": self.id,
            "palabra": self.palabra,
            "definicion": self.definicion,
            "categoria": self.categoria,
            "campo_relacionado": self.campo_relacionado,
            "tabla_relacionada": self.tabla_relacionada,
            "sinonimos": json.loads(self.sinonimos) if self.sinonimos else [],
            "ejemplos_uso": json.loads(self.ejemplos_uso) if self.ejemplos_uso else [],
            "activo": self.activo,
            "orden": self.orden,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
            "actualizado_en": self.actualizado_en.isoformat() if self.actualizado_en else None,
        }
