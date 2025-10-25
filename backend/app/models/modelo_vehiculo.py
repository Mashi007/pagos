# backend/app/models/modelo_vehiculo.py

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func
from app.db.session import Base


class ModeloVehiculo(Base):

    id = Column(Integer, primary_key=True, index=True)
    modelo = Column(String(100), nullable=False, unique=True, index=True)
    activo = Column(Boolean, nullable=False, default=True, index=True)

    # Timestamps
    updated_at = Column(
    )


    def __repr__(self):
        return (
            f"<ModeloVehiculo(id={self.id}, modelo='{self.modelo}', "
            f"activo={self.activo})>"
        )


    def to_dict(self):
        return {
            "id": self.id,
            "modelo": self.modelo,
            "activo": self.activo,
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at else None
            ),
        }
