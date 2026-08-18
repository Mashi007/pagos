"""
Filas de CONCILIACIÓN / Drive que el admin eliminó de las pantallas de candidatos.

No se borran de Google Sheets; solo se omiten al armar el snapshot de clientes o préstamos
para que no reaparezcan tras sync/refresh.
"""
from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint, func

from app.core.database import Base


class DriveCandidatoEliminadoPasivo(Base):
    __tablename__ = "drive_candidatos_eliminados_pasivos"
    __table_args__ = (
        UniqueConstraint("origen", "cedula_cmp", name="uq_drive_elim_pasivo_origen_cedula"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    # 'cliente' | 'prestamo' (cédula) | 'prestamo_fila' (sheet_row ya convertida en préstamo)
    origen = Column(String(16), nullable=False, index=True)
    cedula_cmp = Column(String(32), nullable=False, index=True)
    sheet_row_number = Column(Integer, nullable=True, index=True)
    usuario_email = Column(String(255), nullable=True)
    eliminado_en = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
