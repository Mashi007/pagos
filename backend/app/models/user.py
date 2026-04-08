"""
Modelo SQLAlchemy para Usuario (auth y gestión de usuarios).
Tabla: usuarios. Campos: email, cedula, password_hash, nombre (nombre completo), cargo, rol, is_active, timestamps.

Tras migración 041_merge_nombre_apellido: no existe columna apellido; nombre es VARCHAR(255) con nombre y apellido unidos.

Roles estandarizados según RBAC (Role-Based Access Control - ISO/IEC 12207):
  - admin: Acceso total (Administrador del Sistema)
  - manager: Gestión de operaciones (Gerente/Supervisor)
  - operator: Operaciones básicas (Operario)
  - viewer: Solo lectura (Visualizador)
"""
from sqlalchemy import Boolean, Column, DateTime, Integer, String, text

from app.core.database import Base


class User(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    cedula = Column(String(50), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    nombre = Column(String(255), nullable=False)
    cargo = Column(String(100), nullable=True)
    rol = Column(String(20), nullable=False, server_default=text("'viewer'"))
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    created_at = Column(DateTime(timezone=False), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=False), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    last_login = Column(DateTime(timezone=False), nullable=True)
