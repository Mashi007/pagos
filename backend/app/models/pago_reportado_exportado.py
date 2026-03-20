"""
Registro persistente de pagos reportados aprobados ya exportados.
"""
from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.core.database import Base


class PagoReportadoExportado(Base):
    __tablename__ = "pagos_reportados_exportados"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    pago_reportado_id = Column(
        Integer,
        ForeignKey("pagos_reportados.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    created_at = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
