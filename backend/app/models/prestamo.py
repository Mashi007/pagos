from sqlalchemy import Column, Integer, String, Date, TIMESTAMP, Text, Numeric, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base

class Prestamo(Base):
    __tablename__ = "prestamos"
    __table_args__ = {"schema": "pagos_sistema"}
    
    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("pagos_sistema.clientes.id"), nullable=False)
    codigo_prestamo = Column(String(20), unique=True, index=True)
    
    # Montos
    monto_total = Column(Numeric(12, 2), nullable=False)
    monto_financiado = Column(Numeric(12, 2), nullable=False)
    monto_inicial = Column(Numeric(12, 2), default=0.00)
    tasa_interes = Column(Numeric(5, 2), default=0.00)
    
    # Cuotas
    numero_cuotas = Column(Integer, nullable=False)
    monto_cuota = Column(Numeric(12, 2), nullable=False)
    cuotas_pagadas = Column(Integer, default=0)
    cuotas_pendientes = Column(Integer)
    
    # Fechas
    fecha_aprobacion = Column(Date, nullable=False)
    fecha_desembolso = Column(Date)
    fecha_primer_vencimiento = Column(Date, nullable=False)
    fecha_ultimo_vencimiento = Column(Date)
    
    # Estado financiero
    saldo_pendiente = Column(Numeric(12, 2), nullable=False)
    saldo_capital = Column(Numeric(12, 2), nullable=False)
    saldo_interes = Column(Numeric(12, 2), default=0.00)
    total_pagado = Column(Numeric(12, 2), default=0.00)
    
    # Estado
    estado = Column(String(20), default="ACTIVO")
    categoria = Column(String(20), default="NORMAL")
    modalidad = Column(String(20), default="TRADICIONAL")
    
    # Información adicional
    destino_credito = Column(Text)
    observaciones = Column(Text)
    
    # Auditoría
    creado_en = Column(TIMESTAMP, server_default=func.now())
    actualizado_en = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Relaciones
    cliente = relationship("Cliente", backref="prestamos")
