from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base

class Analista(Base):
    __tablename__ = "analistas"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False, index=True)
    apellido = Column(String(255), nullable=True, index=True)
    email = Column(String(255), nullable=True, unique=True, index=True)
    telefono = Column(String(20), nullable=True)
    especialidad = Column(String(255), nullable=True)  # Ej: "Vehículos nuevos", "Usados", "Comercial"
    comision_porcentaje = Column(Integer, nullable=True)  # Porcentaje de comisión (0-100)
    activo = Column(Boolean, default=True, nullable=False)
    notas = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    clientes = relationship("Cliente", back_populates="asesor_config_rel")

    def __repr__(self):
        return f"<Analista(id={self.id}, nombre='{self.nombre_completo}', activo={self.activo})>"

    @property
    def nombre_completo(self):
        if self.apellido:
            return f"{self.nombre} {self.apellido}".strip()
        return self.nombre

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "activo": self.activo,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
