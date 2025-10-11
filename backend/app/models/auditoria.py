# backend/app/models/auditoria.py
"""
Modelo de Auditoría
Registra todas las acciones importantes del sistema para trazabilidad
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from app.db.base import Base


class Auditoria(Base):
    """
    Modelo de Auditoría para registro de acciones del sistema
    """
    __tablename__ = "auditorias"
    
    # Identificación
    id = Column(Integer, primary_key=True, index=True)
    
    # Usuario que realizó la acción
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Acción realizada
    accion = Column(
        String(50),
        nullable=False,
        index=True
    )  # CREATE, UPDATE, DELETE, LOGIN, LOGOUT, etc.
    
    # Entidad afectada
    entidad = Column(
        String(50),
        nullable=False,
        index=True
    )  # Cliente, Prestamo, Pago, User, etc.
    
    entidad_id = Column(Integer, nullable=True, index=True)
    
    # Descripción de la acción
    descripcion = Column(Text, nullable=True)
    
    # Datos relevantes (JSON)
    datos_anteriores = Column(JSON, nullable=True)  # Estado antes del cambio
    datos_nuevos = Column(JSON, nullable=True)      # Estado después del cambio
    
    # Metadata
    ip_address = Column(String(45), nullable=True)  # IPv4 o IPv6
    user_agent = Column(String(255), nullable=True)
    
    # Resultado de la acción
    resultado = Column(
        String(20),
        nullable=False,
        default="EXITOSO"
    )  # EXITOSO, FALLIDO, PARCIAL
    
    mensaje_error = Column(Text, nullable=True)
    
    # Timestamp
    creado_en = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    
    # Relaciones
    user = relationship("User", back_populates="auditorias")
    
    def __repr__(self):
        return f"<Auditoria {self.accion} - {self.entidad} - {self.creado_en}>"
    
    @classmethod
    def registrar(
        cls,
        user_id: int,
        accion: str,
        entidad: str,
        entidad_id: int = None,
        descripcion: str = None,
        datos_anteriores: dict = None,
        datos_nuevos: dict = None,
        ip_address: str = None,
        user_agent: str = None,
        resultado: str = "EXITOSO",
        mensaje_error: str = None
    ):
        """
        Método helper para crear registros de auditoría
        
        Args:
            user_id: ID del usuario que realizó la acción
            accion: Tipo de acción (CREATE, UPDATE, DELETE, etc.)
            entidad: Tipo de entidad afectada
            entidad_id: ID de la entidad afectada
            descripcion: Descripción de la acción
            datos_anteriores: Estado anterior (dict)
            datos_nuevos: Estado nuevo (dict)
            ip_address: IP del usuario
            user_agent: User agent del navegador
            resultado: Resultado de la acción
            mensaje_error: Mensaje de error si falló
            
        Returns:
            Auditoria: Instancia del registro de auditoría
        """
        return cls(
            user_id=user_id,
            accion=accion,
            entidad=entidad,
            entidad_id=entidad_id,
            descripcion=descripcion,
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos,
            ip_address=ip_address,
            user_agent=user_agent,
            resultado=resultado,
            mensaje_error=mensaje_error
        )
