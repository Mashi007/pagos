"""
Modelo SQLAlchemy para datos temporales de conciliación (Excel cargado por cédula).
Se eliminan al descargar el reporte Conciliación.
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, text
from sqlalchemy.sql import func

from app.core.database import Base


class ConciliacionTemporal(Base):
    __tablename__ = "conciliacion_temporal"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cedula = Column(String(20), nullable=False, index=True)
    total_financiamiento = Column(Numeric(14, 2), nullable=False)
    total_abonos = Column(Numeric(14, 2), nullable=False)
    columna_e = Column(String(255), nullable=True)
    columna_f = Column(String(255), nullable=True)
    creado_en = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
