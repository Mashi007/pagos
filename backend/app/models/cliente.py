# backend/app/models/cliente.py
from sqlalchemy import Column, Integer, String, Date, TIMESTAMP, Text, Boolean, Numeric, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base

class Cliente(Base):
    __tablename__ = "clientes"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Documento - OBLIGATORIO
    # CORREGIDO: Removido unique=True para permitir múltiples clientes con misma cédula
    cedula = Column(String(20), nullable=False, index=True)
    
    # Datos personales - OBLIGATORIOS
    nombres = Column(String(100), nullable=False)  # 1-2 palabras máximo
    apellidos = Column(String(100), nullable=False)  # 1-2 palabras máximo
    telefono = Column(String(15), nullable=False, index=True)  # Validado por validadores
    email = Column(String(100), nullable=False, index=True)  # Validado por validadores
    direccion = Column(Text, nullable=False)  # Libre
    fecha_nacimiento = Column(Date, nullable=False)  # Validado por validadores
    ocupacion = Column(String(100), nullable=False)  # Texto libre
    
    # ============================================
    # DATOS DEL VEHÍCULO Y FINANCIAMIENTO - OBLIGATORIOS
    # ============================================
    # Campos de configuración necesarios para formulario y Excel
    modelo_vehiculo = Column(String(100), nullable=False, index=True)  # Configuración
    concesionario = Column(String(100), nullable=False, index=True)  # Configuración
    analista = Column(String(100), nullable=False, index=True)  # Configuración
    
    # Estado y control - OBLIGATORIOS
    estado = Column(String(20), nullable=False, default="ACTIVO", index=True)  # Activo/Inactivo/Finalizado
    activo = Column(Boolean, nullable=False, default=True, index=True)
    
    # Auditoría - OBLIGATORIOS
    fecha_registro = Column(TIMESTAMP, nullable=False, default=func.now())  # Validado por validadores
    fecha_actualizacion = Column(TIMESTAMP, nullable=False, default=func.now(), onupdate=func.now())  # Automático
    usuario_registro = Column(String(100), nullable=False)  # Email del usuario logueado (automático)
    
    # Notas - OPCIONAL
    notas = Column(Text, nullable=True, default="NA")  # Si no llena "NA"
    
    # ============================================
    # RELACIONES CON OTROS MODELOS
    # ============================================
    # NOTA: Todas las relaciones comentadas porque las tablas son solo plantillas vacías
    # asesor_config_rel = relationship("Analista", back_populates="clientes")
    # prestamos = relationship("Prestamo", back_populates="cliente", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Cliente(id={self.id}, cedula='{self.cedula}', nombres='{self.nombres}', apellidos='{self.apellidos}')>"