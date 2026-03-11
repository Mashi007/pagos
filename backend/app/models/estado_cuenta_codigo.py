"""
Código temporal para descarga de estado de cuenta público.
Flujo: usuario ingresa cédula -> se envía código al email -> usuario ingresa código -> se permite descargar PDF.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime

from app.core.database import Base


class EstadoCuentaCodigo(Base):
    __tablename__ = "estado_cuenta_codigos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cedula_normalizada = Column(String(20), nullable=False, index=True)
    email = Column(String(100), nullable=False)
    codigo = Column(String(10), nullable=False)
    expira_en = Column(DateTime(timezone=False), nullable=False)
    usado = Column(Boolean, nullable=False, default=False)
    creado_en = Column(DateTime(timezone=False), nullable=False)
