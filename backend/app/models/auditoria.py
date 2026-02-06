"""
Modelo SQLAlchemy para Auditoría. Persiste eventos de auditoría en BD.
Alineado con tabla real: id, usuario_id, accion, entidad, entidad_id, detalles,
ip_address, user_agent, exito, mensaje_error, fecha.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func

from app.core.database import Base


class Auditoria(Base):
    __tablename__ = "auditoria"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    usuario_id = Column(Integer, nullable=False, index=True)
    accion = Column(String(100), nullable=False, index=True)
    entidad = Column(String(100), nullable=False, index=True)
    entidad_id = Column(Integer, nullable=True, index=True)
    detalles = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    exito = Column(Boolean, nullable=False, default=True)
    mensaje_error = Column(Text, nullable=True)
    fecha = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
