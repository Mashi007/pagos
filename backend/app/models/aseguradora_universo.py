"""Universo de cedulas del informe Aseguradora (Google Sheet)."""

from sqlalchemy import Column, DateTime, Integer, String, func

from app.core.database import Base


class AseguradoraUniversoCedula(Base):
    __tablename__ = "aseguradora_universo_cedulas"

    cedula = Column(String(20), primary_key=True)
    creado_en = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    usuario_id = Column(Integer, nullable=True)
