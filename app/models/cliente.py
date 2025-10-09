# app/models/cliente.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base

class Cliente(Base):
    __tablename__ = "clientes"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False, index=True)
    cedula = Column(String, unique=True, nullable=False, index=True)
    telefono = Column(String, nullable=False)
    email = Column(String, nullable=True)
    direccion = Column(String, nullable=True)
    activo = Column(Boolean, default=True)
    
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    prestamos = relationship("Prestamo", back_populates="cliente")
    
    def __repr__(self):
        return f"<Cliente {self.nombre} - {self.cedula}>"
