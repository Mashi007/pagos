"""
Modelo de Usuario
Tabla de usuarios del sistema con autenticación y roles
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base
from app.core.permissions import UserRole
class User(Base):
    """Modelo de Usuario"""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    rol = Column(SQLEnum(UserRole), nullable=False, default=UserRole.COBRANZAS)
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
        return f"<User(id={self.id}, email='{self.email}', rol='{self.rol}')>"
    
    @property
    def full_name(self) -> str:
        """Retorna el nombre completo del usuario"""
        return f"{self.nombre} {self.apellido}"
