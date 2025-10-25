"""
Modelo de Usuario Simplificado
Solo 2 roles: ADMIN (acceso completo) y USER (acceso limitado)
"""

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base

EMAIL_LENGTH = 255
NAME_LENGTH = 100
PASSWORD_LENGTH = 255


class User(Base):
    """Modelo de Usuario Simplificado"""


    id = Column(Integer, primary_key=True, index=True)
    email = Column(
        String(EMAIL_LENGTH), unique=True, index=True, nullable=False
    )
    nombre = Column(String(NAME_LENGTH), nullable=False)
    apellido = Column(String(NAME_LENGTH), nullable=False)
    hashed_password = Column(String(PASSWORD_LENGTH), nullable=False)
    is_admin = Column(
        Boolean, default=False, nullable=False
    )  # Cambio clave: rol → is_admin
    cargo = Column(
        String(NAME_LENGTH), nullable=True
    )  # Campo separado para cargo en la empresa
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(
    )

    # Relaciones
    aprobaciones_solicitadas = relationship(
        "Aprobacion",
        foreign_keys="Aprobacion.solicitante_id",
        back_populates="solicitante",
    )
    aprobaciones_revisadas = relationship(
        "Aprobacion",
        foreign_keys="Aprobacion.revisor_id",
        back_populates="revisor",
    )

    auditorias = relationship("Auditoria", back_populates="usuario")
    notificaciones = relationship("Notificacion", back_populates="user")


    def __repr__(self):
        return (
            f"<User(id={self.id}, email='{self.email}', "
            f"is_admin={self.is_admin})>"
        )

    @property
    def full_name(self) -> str:
        """Retorna el nombre completo del usuario"""
        return f"{self.nombre} {self.apellido}"

    @property
    def rol(self) -> str:
        """Propiedad para compatibilidad hacia atrás"""
        return "ADMIN" if self.is_admin else "USER"
