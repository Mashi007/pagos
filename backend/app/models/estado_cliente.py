"""Modelo para estados de cliente (dropdown en formularios)."""
from sqlalchemy import Column, Integer, String

from app.core.database import Base


class EstadoCliente(Base):
    __tablename__ = "estados_cliente"

    valor = Column(String(20), primary_key=True)
    etiqueta = Column(String(50), nullable=False)
    orden = Column(Integer, nullable=False, default=0)
