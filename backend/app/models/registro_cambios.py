"""
Modelo SQLAlchemy para Registro de Cambios.
Tabla: registro_cambios - Almacena todos los cambios realizados en el sistema con trazabilidad completa.
Campos: usuario_id, usuario_email, fecha_hora, modulo, descripcion, campos_anteriores, campos_nuevos, registro_id, tipo_cambio.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.core.database import Base


class RegistroCambios(Base):
    __tablename__ = "registro_cambios"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    usuario_email = Column(String(255), nullable=True)
    modulo = Column(String(100), nullable=False, index=True)
    tipo_cambio = Column(String(50), nullable=False, index=True)  # CREAR, ACTUALIZAR, ELIMINAR, etc.
    descripcion = Column(Text, nullable=False)
    registro_id = Column(Integer, nullable=True, index=True)  # ID del registro afectado
    tabla_afectada = Column(String(100), nullable=True)
    campos_anteriores = Column(JSONB, nullable=True)  # JSON con valores anteriores
    campos_nuevos = Column(JSONB, nullable=True)  # JSON con valores nuevos
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    fecha_hora = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    vigente = Column(Boolean, nullable=False, default=True)
