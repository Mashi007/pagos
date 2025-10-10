# backend/app/models/auditoria.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base
from app.core.constants import TipoMovimiento


class Auditoria(Base):
    __tablename__ = "auditorias"
    __table_args__ = {"schema": "pagos_sistema"}  # ✅ AGREGAR SCHEMA
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Usuario que realizó la acción
    usuario_id = Column(Integer, ForeignKey("pagos_sistema.users.id"), nullable=False)  # ✅ CON SCHEMA
    
    # Tipo de acción
    tipo_movimiento = Column(String, nullable=False)  # CREACION, ACTUALIZACION, etc.
    
    # Detalles de la acción
    entidad = Column(String, nullable=False)  # Cliente, Prestamo, Pago, etc.
    entidad_id = Column(Integer, nullable=True)  # ID del registro afectado
    
    # Datos
    descripcion = Column(Text, nullable=False)
    datos_anteriores = Column(JSON, nullable=True)  # Estado antes del cambio
    datos_nuevos = Column(JSON, nullable=True)      # Estado después del cambio
    
    # Metadata
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    
    # Fecha
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    usuario = relationship("User", back_populates="auditorias", foreign_keys=[usuario_id])
    
    def __repr__(self):
        return f"<Auditoria {self.tipo_movimiento} - {self.entidad} #{self.entidad_id}>"
