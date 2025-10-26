"""
Modelo para almacenar logos de la empresa en PostgreSQL
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, LargeBinary, String

from app.db.base import Base


class Logo(Base):
    """
    Modelo para almacenar logos de la empresa en PostgreSQL como BYTEA
    """

    __tablename__ = "logos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False, unique=True)
    archivo = Column(LargeBinary, nullable=False)  # BYTEA en PostgreSQL
    tipo_mime = Column(String(50), nullable=False, default="image/png")
    fecha_upload = Column(DateTime, default=datetime.now, nullable=False)
    subido_por = Column(Integer, nullable=True)

    def __repr__(self):
        return f"<Logo(nombre='{self.nombre}', id={self.id})>"

    def to_dict(self):
        """Convierte el logo a diccionario"""
        return {
            "id": self.id,
            "nombre": self.nombre,
            "tipo_mime": self.tipo_mime,
            "fecha_upload": self.fecha_upload.isoformat() if self.fecha_upload else None,
            "subido_por": self.subido_por,
        }
