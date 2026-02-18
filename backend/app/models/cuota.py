"""
Modelo SQLAlchemy para Cuota. Mapeado a la BD real.
Columnas: id, prestamo_id, numero_cuota, fecha_vencimiento, fecha_pago, monto_cuota,
saldo_capital_inicial, saldo_capital_final, total_pagado, dias_mora, estado, observaciones,
es_cuota_especial, creado_en, actualizado_en, dias_morosidad, cliente_id.
"""
from sqlalchemy import Column, Integer, Numeric, Date, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.core.database import Base


class Cuota(Base):
    __tablename__ = "cuotas"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    prestamo_id = Column(Integer, ForeignKey("prestamos.id"), nullable=False, index=True)
    pago_id = Column(Integer, ForeignKey("pagos.id", ondelete="SET NULL"), nullable=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True, index=True)
    numero_cuota = Column(Integer, nullable=False)
    fecha_vencimiento = Column(Date, nullable=False)
    fecha_pago = Column(Date, nullable=True)
    monto = Column("monto_cuota", Numeric(14, 2), nullable=False)
    saldo_capital_inicial = Column(Numeric(14, 2), nullable=False)
    saldo_capital_final = Column(Numeric(14, 2), nullable=False)
    total_pagado = Column(Numeric(14, 2), nullable=True)
    dias_mora = Column(Integer, nullable=True)
    dias_morosidad = Column(Integer, nullable=True)
    estado = Column(String(20), nullable=False)
    observaciones = Column(String(255), nullable=True)
    es_cuota_especial = Column(Boolean, nullable=True)
    creado_en = Column(DateTime(timezone=True), nullable=True, server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
