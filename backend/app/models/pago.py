# backend/app/models/pago.py
from sqlalchemy import Column, Integer, String, Date, Time, TIMESTAMP, Numeric, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class Pago(Base):
    __tablename__ = "pagos"
    
    id = Column(Integer, primary_key=True, index=True)
    prestamo_id = Column(Integer, ForeignKey("prestamos.id"), nullable=False)
    
    # Información del pago
    numero_cuota = Column(Integer, nullable=False)
    codigo_pago = Column(String(30), unique=True, index=True)
    
    # Montos
    monto_cuota_programado = Column(Numeric(12, 2), nullable=False)
    monto_pagado = Column(Numeric(12, 2), nullable=False)
    monto_capital = Column(Numeric(12, 2), default=0.00)
    monto_interes = Column(Numeric(12, 2), default=0.00)
    monto_mora = Column(Numeric(12, 2), default=0.00)
    descuento = Column(Numeric(12, 2), default=0.00)
    monto_total = Column(Numeric(12, 2), nullable=False)
    
    # Fechas
    fecha_pago = Column(Date, nullable=False)
    fecha_vencimiento = Column(Date, nullable=False)
    hora_pago = Column(Time, server_default=func.current_time())
    
    # Mora
    dias_mora = Column(Integer, default=0)
    tasa_mora = Column(Numeric(5, 2), default=0.00)
    
    # Pago
    metodo_pago = Column(String(20), default="EFECTIVO")
    numero_operacion = Column(String(50))
    comprobante = Column(String(50))
    banco = Column(String(50))
    
    # Estado
    estado = Column(String(20), default="PAGADO")
    tipo_pago = Column(String(20), default="NORMAL")
    
    # Información adicional
    observaciones = Column(Text)
    usuario_registro = Column(String(50))
    
    # Auditoría
    creado_en = Column(TIMESTAMP, server_default=func.now())
    
    # Relaciones
    prestamo = relationship("Prestamo", back_populates="pagos")
    cuotas = relationship(
        "Cuota",
        secondary="pago_cuotas",
        back_populates="pagos",
        overlaps="pagos,cuota"
    )
