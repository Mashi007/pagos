"""
Lista de cédulas permitidas para reportar pagos en Bolívares (Bs) en rapicredit-cobros e infopagos.
Se carga desde un Excel con columna 'cedula' en /pagos/pagos.
"""
from sqlalchemy import Column, String
from app.core.database import Base


class CedulaReportarBs(Base):
    __tablename__ = "cedulas_reportar_bs"

    cedula = Column(String(20), primary_key=True)
