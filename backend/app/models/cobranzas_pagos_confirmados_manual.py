"""Override manual de KPI «Pagos confirmados» en Cobranzas (por columna/fecha)."""
from sqlalchemy import Column, Date, DateTime, Integer, Numeric, String, func

from app.core.database import Base


class CobranzasPagosConfirmadosManual(Base):
    __tablename__ = "cobranzas_pagos_confirmados_manual"

    fecha_lectura = Column(Date, primary_key=True)
    cantidad = Column(Integer, nullable=False, default=0)
    monto_usd = Column(Numeric(14, 2), nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(255), nullable=True)
