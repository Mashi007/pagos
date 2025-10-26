from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.db.session import Base


class Concesionario(Base):
    """
    Modelo para concesionarios
    Representa a los concesionarios que venden vehículos
    """

    __tablename__ = "concesionarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False, index=True)
    activo = Column(Boolean, default=True, nullable=False)

    # Timestamps
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Concesionario(id={self.id}, nombre='{self.nombre}', activo={self.activo})>"

    def to_dict(self):
        return {"id": self.id, "nombre": self.nombre, "activo": self.activo}
