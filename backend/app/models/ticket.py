"""
Modelo SQLAlchemy para Ticket (CRM).
Conectado a la tabla clientes vía cliente_id.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import text

from app.core.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    titulo = Column(String(255), nullable=False)
    descripcion = Column(Text, nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True, index=True)
    estado = Column(String(30), nullable=False, default="abierto", index=True)
    prioridad = Column(String(20), nullable=False, default="media")
    tipo = Column(String(30), nullable=False, default="consulta")
    asignado_a = Column(String(255), nullable=True)
    asignado_a_id = Column(Integer, nullable=True)
    escalado_a_id = Column(Integer, nullable=True)
    escalado = Column(Boolean, nullable=False, default=False)
    fecha_limite = Column(DateTime(timezone=False), nullable=True)
    conversacion_whatsapp_id = Column(Integer, nullable=True)
    comunicacion_email_id = Column(Integer, nullable=True)
    creado_por_id = Column(Integer, nullable=True)
    fecha_creacion = Column(DateTime(timezone=False), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    fecha_actualizacion = Column(DateTime(timezone=False), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    archivos = Column(Text, nullable=True)  # JSON array de rutas
