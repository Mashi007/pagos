"""
Modelo SQLAlchemy para CuotaPago. Tabla join para historial de pagos por cuota.
Permite rastrear TODOS los pagos que han tocado una cuota, no solo el último.

Relación: Una cuota puede recibir múltiples pagos parciales o completos.
Cada pago aplicado a una cuota genera una entrada en cuota_pagos.
"""
from sqlalchemy import Column, Integer, Numeric, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func

from app.core.database import Base


class CuotaPago(Base):
    """
    Tabla join: cuota ↔ pago. Registra TODOS los pagos aplicados a cada cuota.
    
    Diseño:
    - cuota_id (FK): Referencia a cuota pagada
    - pago_id (FK): Referencia a pago aplicado
    - monto_aplicado: Cuánto del pago se aplicó a esta cuota
    - fecha_aplicacion: Cuándo se aplicó (puede ser diferente a fecha_pago del pago)
    - orden_aplicacion: Secuencia FIFO dentro de los pagos para esta cuota
    - es_pago_completo: Si este pago completó la cuota (100%)
    """
    __tablename__ = "cuota_pagos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cuota_id = Column(Integer, ForeignKey("cuotas.id", ondelete="CASCADE"), nullable=False, index=True)
    pago_id = Column(Integer, ForeignKey("pagos.id", ondelete="CASCADE"), nullable=False, index=True)
    monto_aplicado = Column(Numeric(14, 2), nullable=False)  # Cuánto se aplicó a cuota
    fecha_aplicacion = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    orden_aplicacion = Column(Integer, nullable=False, default=0)  # Secuencia FIFO
    es_pago_completo = Column(Boolean, nullable=False, default=False)  # ¿Completó la cuota?
    creado_en = Column(DateTime(timezone=True), nullable=True, server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
