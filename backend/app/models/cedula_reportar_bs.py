"""
Lista de cédulas permitidas para reportar pagos en Bolívares (Bs) en rapicredit-cobros e infopagos.
Se carga desde un Excel con columna 'cedula' en /pagos/pagos.
"""
from sqlalchemy import Column, DateTime, String, func

from app.core.database import Base


class CedulaReportarBs(Base):
    __tablename__ = "cedulas_reportar_bs"

    cedula = Column(String(20), primary_key=True)
    creado_en = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    # bcv | euro | binance — alineado con PagoReportado / tasa_cambio_service.normalizar_fuente_tasa
    fuente_tasa_cambio = Column(
        String(16),
        nullable=False,
        server_default="euro",
    )
