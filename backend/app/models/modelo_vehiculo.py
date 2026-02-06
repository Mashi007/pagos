"""
Modelo SQLAlchemy para Modelo de Vehículo (catálogo con precio para Valor Activo en préstamos).
"""
from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime
from sqlalchemy.sql import func

from app.core.database import Base


class ModeloVehiculo(Base):
    __tablename__ = "modelos_vehiculos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    modelo = Column(String(255), nullable=False, unique=True, index=True)
    activo = Column(Boolean, nullable=False, default=True)
    precio = Column(Numeric(14, 2), nullable=True)
    created_at = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=False), nullable=False, server_default=func.now(), onupdate=func.now())
