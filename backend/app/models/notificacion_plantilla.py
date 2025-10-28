"""
Modelo de Plantillas de Notificaciones
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.db.session import Base


class NotificacionPlantilla(Base):
    """
    Plantillas de notificaciones con variables dinámicas
    """

    __tablename__ = "notificacion_plantillas"

    id = Column(Integer, primary_key=True, index=True)

    # Identificación
    nombre = Column(String(100), nullable=False, unique=True)
    descripcion = Column(Text, nullable=True)

    # Tipo de notificación
    tipo = Column(
        String(20), nullable=False
    )  # PAGO_5_DIAS_ANTES, PAGO_DIA_0, MORA_1_DIA, etc.

    # Contenido
    asunto = Column(String(200), nullable=False)
    cuerpo = Column(Text, nullable=False)  # Con variables {{nombre}}, {{monto}}, etc.

    # Variables disponibles (JSON en texto para simplicidad)
    variables_disponibles = Column(
        Text, nullable=True
    )  # {"nombre", "monto", "fecha", etc}

    # Estado y control
    activa = Column(Boolean, default=True, nullable=False)
    zona_horaria = Column(String(50), default="America/Caracas", nullable=False)

    # Timestamps
    fecha_creacion = Column(DateTime, server_default=func.now(), nullable=False)
    fecha_actualizacion = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self):
        return f"<NotificacionPlantilla(id={self.id}, nombre='{self.nombre}', tipo='{self.tipo}')>"

    def to_dict(self):
        """Convierte la plantilla a diccionario"""
        return {
            "id": self.id,
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "tipo": self.tipo,
            "asunto": self.asunto,
            "cuerpo": self.cuerpo,
            "variables_disponibles": self.variables_disponibles,
            "activa": self.activa,
            "zona_horaria": self.zona_horaria,
            "fecha_creacion": (
                self.fecha_creacion.isoformat() if self.fecha_creacion else None
            ),
            "fecha_actualizacion": (
                self.fecha_actualizacion.isoformat()
                if self.fecha_actualizacion
                else None
            ),
        }
