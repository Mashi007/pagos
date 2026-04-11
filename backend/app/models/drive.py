"""
Snapshot plano de la hoja Google (CONCILIACIÓN): columnas A a S por fila de datos.
Se rellena en cada sync exitoso (misma corrida que conciliacion_sheet_*).
"""
from sqlalchemy import Column, DateTime, Integer, Text, func

from app.core.database import Base

# Letras A..S (19 columnas), alineadas al rango por defecto CONCILIACION_SHEET_COLUMNS_RANGE=A:S
_DRIVE_LETTERS = "abcdefghijklmnopqrs"


class DriveRow(Base):
    __tablename__ = "drive"

    sheet_row_number = Column(Integer, primary_key=True, nullable=False)
    synced_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    col_a = Column(Text, nullable=True)
    col_b = Column(Text, nullable=True)
    col_c = Column(Text, nullable=True)
    col_d = Column(Text, nullable=True)
    col_e = Column(Text, nullable=True)
    col_f = Column(Text, nullable=True)
    col_g = Column(Text, nullable=True)
    col_h = Column(Text, nullable=True)
    col_i = Column(Text, nullable=True)
    col_j = Column(Text, nullable=True)
    col_k = Column(Text, nullable=True)
    col_l = Column(Text, nullable=True)
    col_m = Column(Text, nullable=True)
    col_n = Column(Text, nullable=True)
    col_o = Column(Text, nullable=True)
    col_p = Column(Text, nullable=True)
    col_q = Column(Text, nullable=True)
    col_r = Column(Text, nullable=True)
    col_s = Column(Text, nullable=True)


DRIVE_COL_COUNT = len(_DRIVE_LETTERS)

DRIVE_COLUMN_NAMES = tuple(f"col_{c}" for c in _DRIVE_LETTERS)
