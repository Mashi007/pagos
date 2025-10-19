# backend/app/models/cliente.py
from sqlalchemy import Column, Integer, String, Date, TIMESTAMP, Text, Boolean, Numeric, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base

class Cliente(Base):
    __tablename__ = "clientes"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Documento
    cedula = Column(String(20), unique=True, nullable=False, index=True)
    
    # Datos personales
    nombres = Column(String(100), nullable=False)
    apellidos = Column(String(100), nullable=False)
    telefono = Column(String(15), nullable=True, index=True)
    email = Column(String(100), nullable=True, index=True)
    direccion = Column(Text, nullable=True)
    fecha_nacimiento = Column(Date, nullable=True)
    ocupacion = Column(String(100), nullable=True)
    
    # ============================================
    # DATOS DEL VEHÍCULO Y FINANCIAMIENTO
    # ============================================
    # Campos de configuración necesarios para formulario y Excel
    modelo_vehiculo = Column(String(100), nullable=True, index=True)
    concesionario = Column(String(100), nullable=True, index=True)
    analista = Column(String(100), nullable=True, index=True)
    
    # Estado y control
    estado = Column(String(20), nullable=True, default="ACTIVO", index=True)
    activo = Column(Boolean, nullable=True, default=True, index=True)
    
    # Auditoría
    fecha_registro = Column(TIMESTAMP, nullable=True, default=func.now())
    fecha_actualizacion = Column(TIMESTAMP, nullable=True, default=func.now(), onupdate=func.now())
    
    # ============================================
    # RELACIONES CON OTROS MODELOS
    # ============================================
    # NOTA: Todas las relaciones comentadas porque las tablas son solo plantillas vacías
    # asesor_config_rel = relationship("Analista", back_populates="clientes")
    # prestamos = relationship("Prestamo", back_populates="cliente", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Cliente(id={self.id}, cedula='{self.cedula}', nombres='{self.nombres}', apellidos='{self.apellidos}')>"