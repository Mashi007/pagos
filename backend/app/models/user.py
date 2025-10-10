# backend/app/models/user.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.session import Base
from app.core.constants import Roles, EstadoUsuario


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Información básica
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    nombre_completo = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    
    # Rol y estado
    rol = Column(SQLEnum(Roles), nullable=False, default=Roles.ASESOR)
    estado = Column(SQLEnum(EstadoUsuario), default=EstadoUsuario.ACTIVO)
    
    # Información adicional
    telefono = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    
    # Seguridad
    is_superuser = Column(Boolean, default=False)
    debe_cambiar_password = Column(Boolean, default=True)
    ultimo_login = Column(DateTime, nullable=True)
    intentos_fallidos = Column(Integer, default=0)
    bloqueado_hasta = Column(DateTime, nullable=True)
    
    # Auditoría
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    creado_por = Column(Integer, nullable=True)
    
    # Relaciones
    auditorias = relationship("Auditoria", back_populates="usuario", foreign_keys="Auditoria.usuario_id")
    notificaciones_enviadas = relationship("Notificacion", back_populates="enviado_por_usuario")
    aprobaciones_solicitadas = relationship(
        "Aprobacion", 
        back_populates="solicitante",
        foreign_keys="Aprobacion.solicitante_id"
    )
    aprobaciones_revisadas = relationship(
        "Aprobacion",
        back_populates="revisor",
        foreign_keys="Aprobacion.revisor_id"
    )
    
    def __repr__(self):
        return f"<User {self.username} - {self.rol}>"
    
    @property
    def is_active(self) -> bool:
        """Verificar si el usuario está activo"""
        return self.estado == EstadoUsuario.ACTIVO
    
    @property
    def is_blocked(self) -> bool:
        """Verificar si el usuario está bloqueado"""
        if self.bloqueado_hasta is None:
            return False
        return datetime.utcnow() < self.bloqueado_hasta
