"""
Modelo de Usuario Simplificado
Solo 2 roles: ADMIN (acceso completo) y USER (acceso limitado)
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base


class User(Base):
    """Modelo de Usuario Simplificado"""
    
    __tablename__ = "usuarios"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)  # Cambio clave: rol → is_admin
    cargo = Column(String(100), nullable=True)  # Campo separado para cargo en la empresa
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # Relaciones
    aprobaciones_solicitadas = relationship(
        "Aprobacion",
        foreign_keys="Aprobacion.solicitante_id",
        back_populates="solicitante"
    )
    aprobaciones_revisadas = relationship(
        "Aprobacion",
        foreign_keys="Aprobacion.revisor_id",
        back_populates="revisor"
    )
    
    # Relación removida: Los préstamos pertenecen a Cliente, no a User
    
    auditorias = relationship("Auditoria", back_populates="usuario")
    notificaciones = relationship("Notificacion", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', is_admin={self.is_admin})>"
    
    @property
    def full_name(self) -> str:
        """Retorna el nombre completo del usuario"""
        return f"{self.nombre} {self.apellido}"
    
    @property
    def rol(self) -> str:
        """Propiedad para compatibilidad hacia atrás"""
        return "ADMIN" if self.is_admin else "USER"
