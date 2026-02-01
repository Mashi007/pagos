"""
Modelo SQLAlchemy para Cuota (cuotas de préstamo por cliente).
Usado para notificaciones: fecha_vencimiento, pagado, días hasta/desde vencimiento.
"""
from sqlalchemy import Column, Integer, Numeric, Date, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import text

from app.core.database import Base


class Cuota(Base):
    __tablename__ = "cuotas"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    numero_cuota = Column(Integer, nullable=False)
    fecha_vencimiento = Column(Date, nullable=False)
    monto = Column(Numeric(14, 2), nullable=False)
    pagado = Column(Boolean, nullable=False, default=False)
    fecha_pago = Column(DateTime(timezone=False), nullable=True)
