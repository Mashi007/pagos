"""
Modelo de Documento AI
Almacena documentos para contexto de respuestas con ChatGPT
"""

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.db.session import Base


class DocumentoAI(Base):
    """
    Documento para contexto de respuestas AI
    """

    __tablename__ = "documentos_ai"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(255), nullable=False)
    descripcion = Column(Text, nullable=True)

    # Información del archivo
    nombre_archivo = Column(String(255), nullable=False)
    tipo_archivo = Column(String(50), nullable=False)  # pdf, txt, docx, etc.
    ruta_archivo = Column(String(500), nullable=False)  # Ruta donde se almacena el archivo
    tamaño_bytes = Column(Integer, nullable=True)

    # Contenido procesado
    contenido_texto = Column(Text, nullable=True)  # Texto extraído del documento
    contenido_procesado = Column(Boolean, default=False)  # Si ya se procesó el contenido

    # Embeddings (opcional, para búsqueda semántica avanzada)
    # Se puede almacenar como JSON o en tabla separada

    # Estado
    activo = Column(Boolean, default=True)

    # Auditoría
    creado_en = Column(DateTime, server_default=func.now())
    actualizado_en = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<DocumentoAI {self.titulo} ({self.tipo_archivo})>"

    def to_dict(self, incluir_contenido: bool = False):
        """
        Convierte el documento a diccionario

        Args:
            incluir_contenido: Si True, incluye el contenido_texto (puede ser grande)
        """
        result = {
            "id": self.id,
            "titulo": self.titulo,
            "descripcion": self.descripcion,
            "nombre_archivo": self.nombre_archivo,
            "tipo_archivo": self.tipo_archivo,
            "tamaño_bytes": self.tamaño_bytes,
            "contenido_procesado": self.contenido_procesado,
            "activo": self.activo,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
            "actualizado_en": self.actualizado_en.isoformat() if self.actualizado_en else None,
        }

        if incluir_contenido:
            result["contenido_texto"] = self.contenido_texto

        return result
