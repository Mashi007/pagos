"""
Modelo para estado de conversación del flujo de cobranza por WhatsApp.
Flujo: esperando_cedula → esperando_confirmacion (Sí/No, máx. 3 intentos) → esperando_foto (intento 1/2/3) → guardado.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import text

from app.core.database import Base


class ConversacionCobranza(Base):
    __tablename__ = "conversacion_cobranza"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    telefono = Column(String(30), nullable=False, unique=True, index=True)
    cedula = Column(String(20), nullable=True)
    nombre_cliente = Column(String(100), nullable=True)
    estado = Column(String(30), nullable=False, default="esperando_cedula")
    intento_foto = Column(Integer, nullable=False, default=0)
    intento_confirmacion = Column(Integer, nullable=False, default=0)
    observacion = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=False), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=False), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
