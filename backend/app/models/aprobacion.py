# backend/app/models/aprobacion.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.session import Base
from app.core.constants import EstadoAprobacion


class Aprobacion(Base):
    __tablename__ = "aprobaciones"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Estado
    estado = Column(SQLEnum(EstadoAprobacion), default=EstadoAprobacion.PENDIENTE)
    
    # Solicitante y revisor
    solicitante_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    revisor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Detalles de la solicitud
    tipo_solicitud = Column(String, nullable=False)  # PRESTAMO, MODIFICACION_MONTO, etc.
    entidad = Column(String, nullable=False)  # Cliente, Prestamo, etc.
    entidad_id = Column(Integer, nullable=False)
    
    # Justificación y comentarios
    justificacion = Column(Text, nullable=False)
    comentarios_revisor = Column(Text, nullable=True)
    
    # Datos de la solicitud
    datos_solicitados = Column(Text, nullable=True)  # JSON string
    
    # Fechas
    fecha_solicitud = Column(DateTime, default=datetime.utcnow)
    fecha_revision = Column(DateTime, nullable=True)
    
    # Relaciones
    solicitante = relationship("User", back_populates="aprobaciones_solicitadas", foreign_keys=[solicitante_id])
    revisor = relationship("User", back_populates="aprobaciones_revisadas", foreign_keys=[revisor_id])
    
    def __repr__(self):
        return f"<Aprobacion {self.tipo_solicitud} - {self.estado}>"
