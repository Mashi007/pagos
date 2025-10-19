from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base

class Analista(Base):
    __tablename__ = "analistas"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False, index=True)  # Nombre completo (incluye apellido)
    activo = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    clientes = relationship("Cliente", back_populates="asesor_config_rel")

    def __repr__(self):
        return f"<Analista(id={self.id}, nombre='{self.nombre}', activo={self.activo})>"

    @property
    def nombre_completo(self):
        """Retorna el nombre completo (que ya está en la columna nombre)"""
        return self.nombre

    @property
    def apellido(self):
        """Extrae el apellido del nombre completo"""
        if self.nombre:
            partes = self.nombre.strip().split()
            if len(partes) > 1:
                return ' '.join(partes[1:])  # Todo después del primer nombre
        return ""

    @property
    def primer_nombre(self):
        """Extrae el primer nombre del nombre completo"""
        if self.nombre:
            partes = self.nombre.strip().split()
            if len(partes) > 0:
                return partes[0]
        return ""

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "primer_nombre": self.primer_nombre,
            "apellido": self.apellido,
            "activo": self.activo,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
