# app/models/pago.py
"""
Modelo Pago - basado en pestaña "Pagos" del Excel
Campos del Excel:
- Columna A: Cédula (Foreign Key)
- Columna B: Fecha que debió pagar
- Columna C: Fecha de pago efectiva
- Columna D: Monto pagado
- Columna E: Documento/Referencia
"""
from sqlalchemy import Column, String, Integer, Float, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base

class Pago(Base):
    __tablename__ = "pagos"
    
    # ID autoincremental
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Relación con cliente (Foreign Key a Cédula)
    cedula_cliente = Column(
        String(20), 
        ForeignKey("clientes.cedula", ondelete="CASCADE"), 
        nullable=False, 
        index=True,
        comment="Cédula del cliente"
    )
    
    # Fechas
    fecha_programada = Column(Date, nullable=False, index=True, comment="Fecha que debió pagar")
    fecha_efectiva = Column(Date, nullable=True, index=True, comment="Fecha que realmente pagó")
    
    # Montos
    monto_pagado = Column(Float, default=0, comment="Monto efectivamente pagado")
    
    # Documento de respaldo
    documento_referencia = Column(String(100), comment="Número de documento/referencia bancaria")
    tipo_pago = Column(String(50), comment="Transferencia, Efectivo, Cheque, etc.")
    banco = Column(String(100), comment="Banco de origen del pago")
    
    # Estado del pago
    pagado = Column(Integer, default=0, comment="0=No pagado, 1=Pagado")
    dias_retraso = Column(Integer, default=0, comment="Días de retraso respecto a fecha programada")
    
    # Conciliación bancaria
    conciliado = Column(Integer, default=0, comment="0=No conciliado, 1=Conciliado")
    fecha_conciliacion = Column(Date, nullable=True, comment="Fecha de conciliación bancaria")
    
    # Notas
    observaciones = Column(Text, comment="Observaciones del pago")
    
    # Auditoría
    fecha_registro = Column(DateTime, default=datetime.utcnow)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relación con cliente
    cliente = relationship("Cliente", back_populates="pagos")
    
    def __repr__(self):
        return f"<Pago {self.id} - Cliente {self.cedula_cliente} - ${self.monto_pagado}>"
