"""
Modelo SQLAlchemy para variables personalizadas de notificaciones.
Tabla: variables_notificacion. Usadas en plantillas como {{nombre_variable}}.
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, func

from app.core.database import Base


class VariableNotificacion(Base):
    __tablename__ = "variables_notificacion"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre_variable = Column(String(80), nullable=False, unique=True, index=True)
    tabla = Column(String(80), nullable=False)  # clientes, prestamos, cuotas, pagos
    campo_bd = Column(String(120), nullable=False)
    descripcion = Column(Text, nullable=True)
    activa = Column(Boolean, nullable=False, default=True)
    fecha_creacion = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
    fecha_actualizacion = Column(DateTime(timezone=False), nullable=False, server_default=func.now(), onupdate=func.now())
