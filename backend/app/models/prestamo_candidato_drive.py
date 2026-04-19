"""
Snapshot de filas CONCILIACIÓN (tabla `drive`) candidatas a préstamo nuevo:
cédula columna E normalizada sin ningún registro en `prestamos` con esa misma clave.

Se reemplaza por completo en cada job programado (domingo y miércoles ~04:05 Caracas).
"""
from sqlalchemy import Column, DateTime, Integer, JSON, String, func

from app.core.database import Base


class PrestamoCandidatoDrive(Base):
    __tablename__ = "prestamo_candidatos_drive"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sheet_row_number = Column(Integer, nullable=False, index=True)
    cedula_cmp = Column(String(32), nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    computed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
