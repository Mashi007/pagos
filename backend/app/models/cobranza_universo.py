"""Universo de cedulas cargado por Excel para analisis de cobranzas."""

from sqlalchemy import Column, Date, DateTime, Integer, Numeric, String, func

from app.core.database import Base


class CobranzaUniversoCedula(Base):
    __tablename__ = "cobranza_universo_cedulas"

    cedula = Column(String(20), primary_key=True)
    creado_en = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    usuario_id = Column(Integer, nullable=True)


class CobranzaUniversoDesempenoDiario(Base):
    __tablename__ = "cobranza_universo_desempeno_diario"

    fecha = Column(Date, primary_key=True)
    bucket = Column(String(10), primary_key=True)
    monto_usd = Column(Numeric(14, 2), nullable=False, server_default="0")
    cantidad_prestamos = Column(Integer, nullable=False, server_default="0")
    actualizado_en = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
