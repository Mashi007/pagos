"""
Modelo de Documento Embedding
Almacena embeddings vectoriales para búsqueda semántica
"""

import json
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import TypeDecorator, VARCHAR

from app.db.session import Base


class JSONEncodedDict(TypeDecorator):
    """Tipo personalizado para almacenar listas/arrays como JSON"""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return value


class DocumentoEmbedding(Base):
    """
    Embedding vectorial de un documento o chunk de documento
    """

    __tablename__ = "documento_ai_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    
    # Relación con documento
    documento_id = Column(Integer, ForeignKey("documentos_ai.id"), nullable=False, index=True)
    
    # Embedding vectorial (almacenado como JSON)
    embedding = Column(JSONEncodedDict, nullable=False)  # Lista de números flotantes
    
    # Información del chunk
    chunk_index = Column(Integer, nullable=True, default=0)  # Índice del chunk si el documento se dividió
    texto_chunk = Column(Text, nullable=True)  # Texto del chunk
    
    # Metadatos
    modelo_embedding = Column(String(100), nullable=True)  # text-embedding-ada-002, etc.
    dimensiones = Column(Integer, nullable=True)  # Dimensión del vector (1536 para ada-002)
    
    # Auditoría
    creado_en = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    actualizado_en = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relación
    documento = relationship("DocumentoAI", foreign_keys=[documento_id])
    
    def __repr__(self):
        return f"<DocumentoEmbedding {self.id} - doc:{self.documento_id} chunk:{self.chunk_index}>"
    
    def to_dict(self):
        """Convierte el embedding a diccionario"""
        return {
            "documento_id": self.documento_id,
            "embedding": self.embedding,
            "chunk_index": self.chunk_index,
            "texto_chunk": self.texto_chunk,
            "modelo_embedding": self.modelo_embedding,
            "dimensiones": self.dimensiones,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
        }

