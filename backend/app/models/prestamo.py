"""
Modelo SQLAlchemy para Préstamo.
Mapeado a la BD real: fecha_registro, modelo_vehiculo; sin monto_programado/monto_pagado.
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.core.database import Base


class Prestamo(Base):
    __tablename__ = "prestamos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    total_financiamiento = Column(Numeric(14, 2), nullable=False)
    estado = Column(String(20), nullable=False, index=True, default="PENDIENTE")
    concesionario = Column(String(255), nullable=True, index=True)
    modelo = Column("modelo_vehiculo", String(255), nullable=True, index=True)
    analista = Column(String(255), nullable=True, index=True)
    fecha_creacion = Column("fecha_registro", DateTime(timezone=False), nullable=False, server_default=func.now())
    fecha_actualizacion = Column(DateTime(timezone=False), nullable=False, server_default=func.now(), onupdate=func.now())
