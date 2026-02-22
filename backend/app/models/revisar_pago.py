"""
Modelo para tabla revisar_pagos: pagos exportados a Excel para revisión.
Tabla temporal de validación; no interfiere con procesos ni reglas de negocio.
Los pagos registrados aquí se excluyen de la vista "Revisar Pagos".
"""
from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func

from app.core.database import Base


class RevisarPago(Base):
    __tablename__ = "revisar_pagos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    pago_id = Column(Integer, ForeignKey("pagos.id", ondelete="CASCADE"), nullable=False, index=True)
    fecha_exportacion = Column(DateTime(timezone=False), nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("pago_id", name="uq_revisar_pagos_pago_id"),)
