from datetime import date
# backend/app/models/modelo_vehiculo.py

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func
from app.db.session import Base


class ModeloVehiculo(Base):

    id = Column(Integer, primary_key=True, index=True)
    modelo = Column(String(100), nullable=False, unique=True, index=True)
    activo = Column(Boolean, nullable=False, default=True, index=True)

    # Timestamps
    updated_at = Column
    )


    def __repr__(self):
        return 
            f"activo={self.activo})>"
        )


    def to_dict(self):
        return 
        }
