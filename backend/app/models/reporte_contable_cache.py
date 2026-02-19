"""
Modelo para cache del reporte contable.
Una fila por cuota con pago. Política: datos históricos fijos; solo últimos 7 días se actualizan.
"""
from sqlalchemy import Column, Integer, Numeric, Date, String, DateTime, ForeignKey, Index
from sqlalchemy.sql import func

from app.core.database import Base


class ReporteContableCache(Base):
    __tablename__ = "reporte_contable_cache"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cuota_id = Column(Integer, ForeignKey("cuotas.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    cedula = Column(String(20), nullable=False, index=True)
    nombre = Column(String(255), nullable=False)
    tipo_documento = Column(String(50), nullable=False)
    fecha_vencimiento = Column(Date, nullable=False)
    fecha_pago = Column(Date, nullable=False, index=True)
    importe_md = Column(Numeric(14, 2), nullable=False)
    moneda_documento = Column(String(10), nullable=False, server_default="USD")
    tasa = Column(Numeric(14, 4), nullable=False)
    importe_ml = Column(Numeric(14, 2), nullable=False)
    moneda_local = Column(String(10), nullable=False, server_default="Bs.")
    creado_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())

    __table_args__ = (
        Index("idx_reporte_contable_cache_fecha_cedula", "fecha_pago", "cedula"),
    )
