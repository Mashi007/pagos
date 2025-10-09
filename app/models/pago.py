# app/models/pago.py
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base

class Pago(Base):
    __tablename__ = "pagos"
    
    id = Column(Integer, primary_key=True, index=True)
    prestamo_id = Column(Integer, ForeignKey("prestamos.id"), nullable=False)
    
    # Información del pago
    monto_pagado = Column(Numeric(10, 2), nullable=False)
    numero_cuota = Column(Integer, nullable=False)
    fecha_pago = Column(DateTime, nullable=False)
    
    # Referencias
    documento_referencia = Column(String, nullable=True)
    registrado_por = Column(String, default="Sistema")
    
    # Auditoría
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    prestamo = relationship("Prestamo", back_populates="pagos")
    
    def __repr__(self):
        return f"<Pago #{self.id} - Préstamo #{self.prestamo_id} - ${self.monto_pagado}>"
