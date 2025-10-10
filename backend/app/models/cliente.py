# backend/app/models/cliente.py
from sqlalchemy import Column, Integer, String, Date, TIMESTAMP, Text, Boolean
from sqlalchemy.sql import func
from app.db.session import Base


class Cliente(Base):
    __tablename__ = "clientes"
    __table_args__ = {"schema": "pagos_sistema"}
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Documento
    cedula = Column(String(20), unique=True, nullable=False, index=True)
    
    # Datos personales
    nombres = Column(String(100), nullable=False)
    apellidos = Column(String(100), nullable=False)
    telefono = Column(String(15), nullable=True)
    email = Column(String(100), nullable=True)
    direccion = Column(Text, nullable=True)
    fecha_nacimiento = Column(Date, nullable=True)
    ocupacion = Column(String(100), nullable=True)
    
    # Estado - CON VALORES POR DEFECTO
    estado = Column(String(20), nullable=False, default="ACTIVO", server_default="ACTIVO")
    activo = Column(Boolean, nullable=False, default=True, server_default="true")
    
    # Auditoría
    fecha_registro = Column(TIMESTAMP, nullable=False, server_default=func.now())
    fecha_actualizacion = Column(TIMESTAMP, nullable=True, onupdate=func.now())
    usuario_registro = Column(String(50), nullable=True)
    
    # Notas
    notas = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<Cliente {self.nombres} {self.apellidos} - {self.cedula}>"
