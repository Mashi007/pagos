"""
Modelo para tabla configuracion (clave-valor). Usado para persistir configuración de email, etc.
"""
from sqlalchemy import Column, String, Text

from app.core.database import Base


class Configuracion(Base):
    __tablename__ = "configuracion"

    clave = Column(String(100), primary_key=True)
    valor = Column(Text, nullable=True)
