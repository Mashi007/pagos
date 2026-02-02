"""
Modelo para imágenes recibidas por WhatsApp (tabla pagos_whatsapp).
Columnas: fecha, cedula_cliente, imagen (binario), link_imagen (Google Drive u otra URL).
"""
from sqlalchemy import Column, Integer, String, LargeBinary, DateTime, Text
from sqlalchemy.sql import text

from app.core.database import Base


class PagosWhatsapp(Base):
    __tablename__ = "pagos_whatsapp"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    fecha = Column(DateTime(timezone=False), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    cedula_cliente = Column(String(20), nullable=True, index=True)
    imagen = Column(LargeBinary, nullable=False)
    link_imagen = Column(Text, nullable=True)
