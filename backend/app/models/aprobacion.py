# backend/app/models/aprobacion.py
"""
Modelo de Aprobación
Sistema de workflow para solicitudes que requieren aprobación
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from app.db.session import Base  # ✅ CORRECTO


class Aprobacion(Base):
    """
    Modelo de Aprobación para workflow de solicitudes
    """
    __tablename__ = "aprobaciones"
    
    # Identificación
    id = Column(Integer, primary_key=True, index=True)
    
    # Estado - Valores posibles: PENDIENTE, APROBADA, RECHAZADA, CANCELADA
    estado = Column(
        String(20),
        nullable=False,
        default="PENDIENTE",
        index=True
    )
    
    # Solicitante y revisor
    solicitante_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    revisor_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Detalles de la solicitud
    tipo_solicitud = Column(
        String(50),
        nullable=False,
        index=True
    )  # PRESTAMO, MODIFICACION_MONTO, ANULACION, etc.
    
    entidad = Column(String(50), nullable=False)  # Cliente, Prestamo, Pago, etc.
    entidad_id = Column(Integer, nullable=False, index=True)
    
    # Justificación y comentarios
    justificacion = Column(Text, nullable=False)
    comentarios_revisor = Column(Text, nullable=True)
    
    # Datos de la solicitud (JSON serializado como string)
    datos_solicitados = Column(Text, nullable=True)
    
    # Fechas
    fecha_solicitud = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    fecha_revision = Column(DateTime(timezone=True), nullable=True)
    
    # Auditoría
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    solicitante = relationship(
        "User",
        foreign_keys=[solicitante_id],
        back_populates="aprobaciones_solicitadas"
    )
    revisor = relationship(
        "User",
        foreign_keys=[revisor_id],
        back_populates="aprobaciones_revisadas"
    )
    
    def __repr__(self):
        return f"<Aprobacion {self.tipo_solicitud} - {self.estado}>"
    
    @property
    def esta_pendiente(self) -> bool:
        """Verifica si la aprobación está pendiente"""
        return self.estado == "PENDIENTE"
    
    @property
    def esta_aprobada(self) -> bool:
        """Verifica si la aprobación fue aprobada"""
        return self.estado == "APROBADA"
    
    @property
    def esta_rechazada(self) -> bool:
        """Verifica si la aprobación fue rechazada"""
        return self.estado == "RECHAZADA"
    
    def aprobar(self, revisor_id: int, comentarios: str = None):
        """Marca la aprobación como aprobada"""
        self.estado = "APROBADA"
        self.revisor_id = revisor_id
        self.comentarios_revisor = comentarios
        self.fecha_revision = datetime.utcnow()
    
    def rechazar(self, revisor_id: int, comentarios: str):
        """Marca la aprobación como rechazada"""
        self.estado = "RECHAZADA"
        self.revisor_id = revisor_id
        self.comentarios_revisor = comentarios
        self.fecha_revision = datetime.utcnow()
    
    def cancelar(self):
        """Cancela la solicitud de aprobación"""
        self.estado = "CANCELADA"
        self.fecha_revision = datetime.utcnow()
