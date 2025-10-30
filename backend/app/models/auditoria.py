"""
Modelo de Auditoría
Registra todas las acciones importantes del sistema para trazabilidad
"""

from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class TipoAccion(str, Enum):
    """Tipos de acciones que se pueden auditar"""

    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    EXPORT = "EXPORT"
    IMPORT = "IMPORT"


class Auditoria(Base):
    """
    Modelo para registrar auditoría del sistema
    Registra todas las acciones importantes para trazabilidad
    """

    __tablename__ = "auditoria"

    id = Column(Integer, primary_key=True, index=True)

    # Usuario que realizó la acción
    usuario_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Detalles de la acción
    accion = Column(
        String(50), nullable=False, index=True
    )  # CREATE, UPDATE, DELETE, etc.
    # Compatibilidad de nombres con BD existente: modulo/registro_id/descripcion/resultado
    entidad = Column(
        "modulo", String(50), nullable=False, index=True
    )  # Cliente, Prestamo, etc.
    entidad_id = Column(
        "registro_id", Integer, nullable=True, index=True
    )  # ID del registro afectado

    # Información adicional
    detalles = Column("descripcion", Text, nullable=True)  # Descripción detallada
    ip_address = Column(String(45), nullable=True)  # IPv4 o IPv6
    user_agent = Column(Text, nullable=True)  # Navegador/dispositivo

    # Resultado de la acción
    # En algunas BD este campo es texto ('EXITOSO'/'FALLIDO'). Usamos String para compatibilidad
    exito = Column("resultado", String(20), nullable=True)
    mensaje_error = Column(Text, nullable=True)  # Mensaje de error si falló

    # Timestamps
    fecha = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Relaciones
    usuario = relationship("User", back_populates="auditorias")

    def __repr__(self):
        return f"<Auditoria {self.accion} - {self.entidad} - {self.fecha}>"

    @classmethod
    def registrar(
        cls,
        usuario_id: int,
        accion: str,
        entidad: str,
        entidad_id: Optional[int] = None,
        detalles: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        exito: bool = True,
        mensaje_error: Optional[str] = None,
    ):
        """
        Registra una acción en el sistema de auditoría

        Args:
            usuario_id: ID del usuario que realizó la acción
            accion: Tipo de acción (CREATE, UPDATE, DELETE, etc.)
            entidad: Tipo de entidad afectada
            entidad_id: ID de la entidad afectada
            detalles: Descripción de la acción
            ip_address: IP del usuario
            user_agent: User agent del navegador
            exito: Si la acción fue exitosa
            mensaje_error: Mensaje de error si falló

        Returns:
            Auditoria: Instancia del registro de auditoría
        """
        return cls(
            usuario_id=usuario_id,
            accion=accion,
            entidad=entidad,
            entidad_id=entidad_id,
            detalles=detalles,
            ip_address=ip_address,
            user_agent=user_agent,
            exito=exito,
            mensaje_error=mensaje_error,
        )

    def to_dict(self):
        """Convierte la auditoría a diccionario"""
        return {
            "id": self.id,
            "usuario_id": self.usuario_id,
            "accion": self.accion,
            "entidad": self.entidad,
            "entidad_id": self.entidad_id,
            "detalles": self.detalles,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "exito": self.exito,
            "mensaje_error": self.mensaje_error,
            "fecha": self.fecha.isoformat() if self.fecha else None,
        }
