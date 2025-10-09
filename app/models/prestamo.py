# app/models/prestamo.py
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.db.session import Base

class EstadoPrestamo(str, enum.Enum):
    ACTIVO = "ACTIVO"
    FINALIZADO = "FINALIZADO"
    MOROSO = "MOROSO"
    CANCELADO = "CANCELADO"

class ModalidadPago(str, enum.Enum):
    SEMANAL = "SEMANAL"
    QUINCENAL = "QUINCENAL"
    MENSUAL = "MENSUAL"

class Prestamo(Base):
    __tablename__ = "prestamos"
    
    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    
    # Información del préstamo
    monto_total = Column(Numeric(10, 2), nullable=False)
    cuotas_totales = Column(Integer, nullable=False)
    modalidad = Column(SQLEnum(ModalidadPago), nullable=False)
    estado = Column(SQLEnum(EstadoPrestamo), default=EstadoPrestamo.ACTIVO)
    
    # Información del vehículo
    modelo_vehiculo = Column(String, nullable=False)
    analista = Column(String, nullable=False)
    concesionario = Column(String, nullable=False)
    
    # Cálculos
    saldo_pendiente = Column(Numeric(10, 2), nullable=False)
    cuotas_pagadas = Column(Integer, default=0)
    
    # Fechas
    fecha_inicio = Column(DateTime, nullable=False)
    proxima_fecha_pago = Column(DateTime, nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    cliente = relationship("Cliente", back_populates="prestamos")
    pagos = relationship("Pago", back_populates="prestamo", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Prestamo #{self.id} - {self.estado.value}>"
