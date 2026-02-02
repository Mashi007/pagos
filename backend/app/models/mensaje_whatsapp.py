"""
Modelo para historial de mensajes WhatsApp (copia de la conversación).
Cada mensaje entrante (webhook) y saliente (bot o manual) se guarda para mostrar en Comunicaciones.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import text

from app.core.database import Base


class MensajeWhatsapp(Base):
    __tablename__ = "mensaje_whatsapp"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    telefono = Column(String(30), nullable=False, index=True)
    direccion = Column(String(10), nullable=False)  # INBOUND | OUTBOUND
    body = Column(Text, nullable=True)  # texto; para imagen puede ser "[Imagen]" o caption
    message_type = Column(String(20), nullable=False, default="text")  # text | image
    timestamp = Column(DateTime(timezone=False), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    created_at = Column(DateTime(timezone=False), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
