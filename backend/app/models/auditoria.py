# backend/app/models/auditoria.py
"""Modelo de Auditoría"""
Registra todas las acciones importantes del sistema para trazabilidad
""""""

from enum import Enum
# from sqlalchemy import  # TODO: Agregar imports específicos
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class TipoAccion(str, Enum):
    """
    """"""
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
    """"""
    Modelo de Auditoría para registro de acciones del sistema
    """"""
    __tablename__ = "auditorias"

    # Identificación
    id = Column(Integer, primary_key=True, index=True)

    # Usuario que realizó la acción
    usuario_id = Column

    # Email del usuario (para ordenamiento rápido)
    usuario_email = Column(String(255), nullable=True, index=True)

    # Acción realizada
    accion = Column
        String(50), nullable=False, index=True
    )  # CREATE, UPDATE, DELETE, LOGIN, LOGOUT, etc.

    # Módulo del sistema
    modulo = Column
        String(50), nullable=False, index=True
    )  # USUARIOS, CLIENTES, PRESTAMOS, PAGOS, etc.

    # Entidad afectada
    tabla = Column
        String(50), nullable=False, index=True
    )  # Cliente, Prestamo, Pago, User, etc.

    registro_id = Column(Integer, nullable=True, index=True)

    # Descripción de la acción
    descripcion = Column(Text, nullable=True)


    # Metadata
    ip_address = Column(String(45), nullable=True)  # IPv4 o IPv6
    user_agent = Column(String(255), nullable=True)

    # Resultado de la acción
    resultado = Column
        String(20), nullable=False, default="EXITOSO"
    )  # EXITOSO, FALLIDO, PARCIAL

    mensaje_error = Column(Text, nullable=True)

    # Timestamp
    fecha = Column
        server_default=func.now(),
        nullable=False,
        index=True,

    # Relaciones
    usuario = relationship("User", back_populates="auditorias")


    def __repr__(self):
        return f"<Auditoria {self.accion} - {self.tabla} - {self.fecha}>"

    @classmethod
    def registrar
        """"""

        Args:
            usuario_id: ID del usuario que realizó la acción
            usuario_email: Email del usuario (para ordenamiento)
            accion: Tipo de acción (CREATE, UPDATE, DELETE, etc.)
            modulo: Módulo del sistema (USUARIOS, CLIENTES, etc.)
            tabla: Tipo de entidad afectada
            registro_id: ID de la entidad afectada
            descripcion: Descripción de la acción
            ip_address: IP del usuario
            user_agent: User agent del navegador
            resultado: Resultado de la acción
            mensaje_error: Mensaje de error si falló

        Returns:
            Auditoria: Instancia del registro de auditoría
        """"""
        return cls
