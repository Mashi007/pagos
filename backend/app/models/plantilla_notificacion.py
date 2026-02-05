"""
Modelo SQLAlchemy para plantillas de notificación (email/WhatsApp por tipo de recordatorio).
Tabla: plantillas_notificacion. Variables en cuerpo/asunto: {{nombre}}, {{cedula}}, {{fecha_vencimiento}}, {{numero_cuota}}, {{monto}}, {{dias_atraso}}.
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, func

from app.core.database import Base


class PlantillaNotificacion(Base):
    __tablename__ = "plantillas_notificacion"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String(255), nullable=False)
    descripcion = Column(Text, nullable=True)
    tipo = Column(String(80), nullable=False, index=True)  # PAGO_5_DIAS_ANTES, PAGO_DIA_0, PREJUDICIAL, MORA_61, etc.
    asunto = Column(String(500), nullable=False)
    cuerpo = Column(Text, nullable=False)
    variables_disponibles = Column(Text, nullable=True)  # JSON o lista separada por coma
    activa = Column(Boolean, nullable=False, default=True)
    zona_horaria = Column(String(80), nullable=False, default="America/Caracas")
    fecha_creacion = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
    fecha_actualizacion = Column(DateTime(timezone=False), nullable=False, server_default=func.now(), onupdate=func.now())
