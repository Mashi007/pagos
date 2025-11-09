"""
Modelo de Variables de Notificaciones
"""

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.db.session import Base


class NotificacionVariable(Base):
    """
    Variables personalizadas para plantillas de notificaciones
    Mapea nombres de variables con campos de la base de datos
    """

    __tablename__ = "notificacion_variables"

    id = Column(Integer, primary_key=True, index=True)

    # Nombre de la variable (ej: nombre_cliente, monto_cuota)
    nombre_variable = Column(String(100), nullable=False, unique=True, index=True)

    # Tabla de la base de datos (clientes, prestamos, cuotas, pagos)
    tabla = Column(String(50), nullable=False)

    # Campo de la base de datos (ej: nombres, monto_cuota, fecha_vencimiento)
    campo_bd = Column(String(100), nullable=False)

    # Descripción de la variable
    descripcion = Column(Text, nullable=True)

    # Estado
    activa = Column(Boolean, default=True, nullable=False, index=True)

    # Timestamps
    fecha_creacion = Column(DateTime, server_default=func.now(), nullable=False)
    fecha_actualizacion = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<NotificacionVariable(id={self.id}, nombre='{self.nombre_variable}', tabla='{self.tabla}.{self.campo_bd}')>"

    def to_dict(self):
        """Convierte la variable a diccionario"""
        return {
            "id": self.id,
            "nombre_variable": self.nombre_variable,
            "tabla": self.tabla,
            "campo_bd": self.campo_bd,
            "descripcion": self.descripcion,
            "activa": self.activa,
            "fecha_creacion": (self.fecha_creacion.isoformat() if self.fecha_creacion else None),
            "fecha_actualizacion": (self.fecha_actualizacion.isoformat() if self.fecha_actualizacion else None),
        }
