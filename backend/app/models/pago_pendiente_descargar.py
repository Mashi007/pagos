"""
Tabla temporal para almacenar pagos reportados aprobados pendientes de descargar.
Se vacía automáticamente después de cada descarga en Excel.
"""
from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.core.database import Base


class PagoPendienteDescargar(Base):
    __tablename__ = "pagos_pendiente_descargar"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    pago_reportado_id = Column(
        Integer,
        ForeignKey("pagos_reportados.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
