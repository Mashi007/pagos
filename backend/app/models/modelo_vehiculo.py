from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.db.session import Base


class ModeloVehiculo(Base):
    """
    Modelo para modelos de vehículos
    Representa los diferentes modelos de vehículos disponibles
    """

    __tablename__ = "modelos_vehiculos"

    id = Column(Integer, primary_key=True, index=True)
    modelo = Column(String(100), nullable=False, unique=True, index=True)
    activo = Column(Boolean, nullable=False, default=True, index=True)

    # Timestamps
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<ModeloVehiculo(id={self.id}, modelo='{self.modelo}', activo={self.activo})>"

    def to_dict(self):
        return {"id": self.id, "modelo": self.modelo, "activo": self.activo}
