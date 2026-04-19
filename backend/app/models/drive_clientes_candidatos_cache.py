"""Caché materializada de candidatos a alta desde Drive (Notificaciones > Clientes)."""
from sqlalchemy import Column, DateTime, Integer, JSON, func

from app.core.database import Base


class DriveClientesCandidatosCache(Base):
    """
    Una sola fila (id=1): último JSON servido por GET /clientes/drive-import/candidatos
    cuando coincide con conciliacion_sheet_meta.synced_at.
    """

    __tablename__ = "drive_clientes_candidatos_cache"

    id = Column(Integer, primary_key=True, autoincrement=False)
    payload = Column(JSON, nullable=False)
    drive_synced_at = Column(DateTime(timezone=True), nullable=True)
    computed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
