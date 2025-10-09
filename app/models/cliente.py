# app/models/cliente.py
"""
Modelo Cliente - basado en pestaña "Clientes" del Excel
Campos del Excel:
- Columna A: Cédula (Primary Key)
- Columna B: Nombre
- Columna C: Móvil
- Columna D: WhatsApp
- Columna E: Email
- Columna F: Estado Caso
- Columna G: Modelo Vehículo
- Columna H: Analista
- Columna I: Concesionario
- Y otros campos...
"""
from sqlalchemy import Column, String, Float, Date, DateTime, Text, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base

class Cliente(Base):
    __tablename__ = "clientes"
    
    # Primary Key - Cédula
    cedula = Column(String(20), primary_key=True, index=True, comment="Cédula de identidad (ej: V12345678)")
    
    # Datos personales
    nombre = Column(String(200), nullable=False, index=True, comment="Nombre completo del cliente")
    movil = Column(String(20), comment="Teléfono móvil principal")
    whatsapp = Column(String(20), comment="Número de WhatsApp")
    email = Column(String(100), comment="Correo electrónico")
    
    # Estado del caso
    estado_caso = Column(String(50), index=True, comment="ACTIVO, CANCELADO, MOROSO, etc.")
    
    # Datos del vehículo/préstamo
    modelo_vehiculo = Column(String(100), comment="Modelo del vehículo financiado")
    analista = Column(String(100), comment="Analista asignado")
    concesionario = Column(String(100), comment="Concesionario de origen")
    
    # Fechas importantes
    fecha_pago_inicial = Column(Date, comment="Fecha del primer pago programado")
    fecha_entrega_vehiculo = Column(Date, comment="Fecha de entrega del vehículo")
    
    # Montos financieros
    total_financiado = Column(Float, comment="Monto total del préstamo")
    cuota_inicial = Column(Float, comment="Cuota inicial/down payment")
    numero_cuotas = Column(Integer, comment="Cantidad de cuotas del préstamo")
    modalidad_financiamiento = Column(String(100), comment="Tipo de financiamiento")
    
    # Control
    requiere_actualizacion = Column(Integer, default=0, comment="1=Requiere actualización, 0=OK")
    observaciones = Column(Text, comment="Notas adicionales del caso")
    
    # Auditoría
    fecha_registro = Column(DateTime, default=datetime.utcnow, comment="Fecha de registro en sistema")
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relación con pagos
    pagos = relationship("Pago", back_populates="cliente", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Cliente {self.cedula} - {self.nombre}>"
