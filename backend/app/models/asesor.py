from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.db.session import Base

class Asesor(Base):
    __tablename__ = "asesores"

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

    def __repr__(self):
        return f"<Asesor(id={self.id}, nombre='{self.nombre_completo}', activo={self.activo})>"

    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}".strip()

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "apellido": self.apellido,
            "nombre_completo": self.nombre_completo,
            "email": self.email,
            "telefono": self.telefono,
            "especialidad": self.especialidad,
            "comision_porcentaje": self.comision_porcentaje,
            "activo": self.activo,
            "notas": self.notas,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
