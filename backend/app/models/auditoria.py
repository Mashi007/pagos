# backend/app/models/auditoria.py
"""
Modelo de Auditoría
Registra todas las acciones importantes del sistema para trazabilidad
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from enum import Enum

from app.db.session import Base  # ✅ CORRECTO


class TipoAccion(str, Enum):
    """
    Enum para los tipos de acciones de auditoría
    """
    CREAR = "CREAR"
    ACTUALIZAR = "ACTUALIZAR" 
    ELIMINAR = "ELIMINAR"
    ANULAR = "ANULAR"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    VER = "VER"
    APROBAR = "APROBAR"
    RECHAZAR = "RECHAZAR"
    ACTIVAR = "ACTIVAR"
    DESACTIVAR = "DESACTIVAR"


class Auditoria(Base):
    """
    Modelo de Auditoría para registro de acciones del sistema
    """
    __tablename__ = "auditorias"
    
    # Identificación
    id = Column(Integer, primary_key=True, index=True)
    
    # Usuario que realizó la acción
    usuario_id = Column(
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
    tabla = Column(
        String(50),
        nullable=False,
        index=True
    )  # Cliente, Prestamo, Pago, User, etc.
    
    registro_id = Column(Integer, nullable=True, index=True)
    
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
    fecha = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    
    # Relaciones
    usuario = relationship("User", back_populates="auditorias")
    
    def __repr__(self):
        return f"<Auditoria {self.accion} - {self.tabla} - {self.fecha}>"
    
    @classmethod
    def registrar(
        cls,
        usuario_id: int,
        accion: str,
        tabla: str,
        registro_id: int = None,
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
            usuario_id: ID del usuario que realizó la acción
            accion: Tipo de acción (CREATE, UPDATE, DELETE, etc.)
            tabla: Tipo de entidad afectada
            registro_id: ID de la entidad afectada
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
            usuario_id=user_id,
            accion=accion,
            tabla=tabla,
            registro_id=registro_id,
            descripcion=descripcion,
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos,
            ip_address=ip_address,
            user_agent=user_agent,
            resultado=resultado,
            mensaje_error=mensaje_error
        )
