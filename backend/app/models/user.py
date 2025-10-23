"""
Modelo de Usuario Simplificado
Solo 2 roles: ADMIN (acceso completo) y USER (acceso limitado)
"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Numeric, JSON, Enum
from sqlalchemy.orm import Session, relationship
from sqlalchemy.sql import func
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.db.session import Base

# Constantes de longitud de campos
EMAIL_LENGTH = 255
NAME_LENGTH = 100
PASSWORD_LENGTH = 255

class User(Base):
    """Modelo de Usuario Simplificado"""

    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(EMAIL_LENGTH), unique=True, index=True, nullable=False)
    nombre = Column(String(NAME_LENGTH), nullable=False)
    apellido = Column(String(NAME_LENGTH), nullable=False)
    hashed_password = Column(String(PASSWORD_LENGTH), nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)  # Cambio clave: rol → is_admin
    cargo = Column(String(NAME_LENGTH), nullable=True)  # Campo separado para cargo en la empresa
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
