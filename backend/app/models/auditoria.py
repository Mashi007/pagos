"""
Modelo SQLAlchemy para Auditoría. Persiste eventos de auditoría en BD.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func

from app.core.database import Base


class Auditoria(Base):
    __tablename__ = "auditoria"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    usuario_id = Column(Integer, nullable=True, index=True)
    usuario_email = Column(String(255), nullable=True, index=True)
    accion = Column(String(100), nullable=False, index=True)
    modulo = Column(String(100), nullable=False, index=True)
    tabla = Column(String(100), nullable=True, index=True)
    registro_id = Column(Integer, nullable=True, index=True)
    descripcion = Column(Text, nullable=True)
    campo = Column(String(100), nullable=True)
    datos_anteriores = Column(Text, nullable=True)
    datos_nuevos = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    resultado = Column(String(50), nullable=False, default="EXITOSO")
    mensaje_error = Column(Text, nullable=True)
    fecha = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
