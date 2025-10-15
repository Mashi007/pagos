from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.db.session import Base

class Concesionario(Base):
    __tablename__ = "concesionarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False, unique=True, index=True)
    direccion = Column(Text, nullable=True)
    telefono = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    responsable = Column(String(255), nullable=True)
    activo = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Concesionario(id={self.id}, nombre='{self.nombre}', activo={self.activo})>"

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "activo": self.activo,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
