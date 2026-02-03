"""
Modelo SQLAlchemy para Usuario (auth y gestión de usuarios).
Tabla: usuarios. Campos: email, password_hash, nombre, apellido, cargo, rol, is_active, timestamps.
Rol: 'administrador' | 'operativo'.
"""
from sqlalchemy import Boolean, Column, DateTime, Integer, String, text

from app.core.database import Base


class User(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False, server_default=text("''"))
    cargo = Column(String(100), nullable=True)
    rol = Column(String(20), nullable=False, server_default=text("'operativo'"))
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    created_at = Column(DateTime(timezone=False), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=False), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    last_login = Column(DateTime(timezone=False), nullable=True)
