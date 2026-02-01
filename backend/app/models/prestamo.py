"""
Modelo SQLAlchemy para Préstamo.
Total financiamiento y métricas de dashboard provienen de prestamos.total_financiamiento
con prestamos.estado = 'APROBADO'.
"""
from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, ForeignKey, text
from sqlalchemy.sql import func

from app.core.database import Base


class Prestamo(Base):
    __tablename__ = "prestamos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    total_financiamiento = Column(Numeric(14, 2), nullable=False)
    estado = Column(String(20), nullable=False, index=True, default="PENDIENTE")  # PENDIENTE, APROBADO, RECHAZADO, etc.
    fecha_creacion = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
    fecha_actualizacion = Column(DateTime(timezone=False), nullable=True, onupdate=func.now())
