from sqlalchemy import Column, Integer, String, Numeric, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base

class Pago(Base):
    """Modelo para gestionar pagos de clientes"""
    __tablename__ = "pagos"

    id = Column(Integer, primary_key=True, index=True)
    
    # DATOS DEL CLIENTE
    cedula_cliente = Column(String(20), nullable=False, index=True)
    
    # DATOS DEL PAGO
    fecha_pago = Column(DateTime, nullable=False)
    monto_pagado = Column(Numeric(12, 2), nullable=False)
    numero_documento = Column(String(100), nullable=False, index=True)
    
    # DOCUMENTO ADJUNTO
    documento_nombre = Column(String(255), nullable=True)
    documento_tipo = Column(String(10), nullable=True)  # PNG, JPG, PDF
    documento_tamaño = Column(Integer, nullable=True)  # bytes
    documento_ruta = Column(String(500), nullable=True)
    
    # ESTADO DE CONCILIACIÓN
    conciliado = Column(Boolean, default=False, nullable=False)
    fecha_conciliacion = Column(DateTime, nullable=True)
    
    # CONTROL Y AUDITORÍA
    activo = Column(Boolean, default=True, nullable=False)
    notas = Column(Text, nullable=True)
    fecha_registro = Column(DateTime, default=func.now(), nullable=False)
    fecha_actualizacion = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # RELACIONES (pendientes hasta desarrollar otros módulos)
    # cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True)
    # cliente = relationship("Cliente", back_populates="pagos")

    def __repr__(self):
        return f"<Pago(id={self.id}, cedula={self.cedula_cliente}, monto={self.monto_pagado}, conciliado={self.conciliado})>"