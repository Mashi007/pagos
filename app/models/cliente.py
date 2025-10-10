from sqlalchemy import Column, Integer, String, Date, TIMESTAMP, Text
from sqlalchemy.sql import func
from app.db.session import Base

class Cliente(Base):
    __tablename__ = "clientes"
    __table_args__ = {"schema": "pagos_sistema"}
    
    id = Column(Integer, primary_key=True, index=True)
    numero_documento = Column(String(20), unique=True, nullable=False, index=True)
    tipo_documento = Column(String(10), default="DNI")
    nombres = Column(String(100), nullable=False)
    apellidos = Column(String(100), nullable=False)
    telefono = Column(String(15))
    email = Column(String(100))
    direccion = Column(Text)
    fecha_nacimiento = Column(Date)
    ocupacion = Column(String(100))
    estado = Column(String(20), default="ACTIVO")
    fecha_registro = Column(TIMESTAMP, server_default=func.now())
    fecha_actualizacion = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    usuario_registro = Column(String(50))
    notas = Column(Text)
