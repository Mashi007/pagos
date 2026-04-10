"""
Snapshot de la hoja CONCILIACIÓN (Google Sheets): metadatos, filas como JSON por cabecera, log de corridas.
"""
from sqlalchemy import Boolean, Column, BigInteger, Integer, String, Text, DateTime, func, text
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class ConciliacionSheetMeta(Base):
    __tablename__ = "conciliacion_sheet_meta"

    id = Column(Integer, primary_key=True)
    spreadsheet_id = Column(String(128), nullable=False, default="")
    sheet_title = Column(String(255), nullable=False, default="")
    headers = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    header_row_index = Column(Integer, nullable=False, default=1)
    row_count = Column(Integer, nullable=False, default=0)
    col_count = Column(Integer, nullable=False, default=0)
    synced_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ConciliacionSheetRow(Base):
    __tablename__ = "conciliacion_sheet_rows"

    row_index = Column(Integer, primary_key=True)
    cells = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))


class ConciliacionSheetSyncRun(Base):
    __tablename__ = "conciliacion_sheet_sync_run"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)
    success = Column(Boolean, nullable=False, default=False)
    message = Column(Text, nullable=True)
    row_count = Column(Integer, nullable=False, default=0)
    col_count = Column(Integer, nullable=False, default=0)
    duration_ms = Column(Integer, nullable=True)
