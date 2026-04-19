"""Auditoría: exportación Excel de candidatos Drive y borrado de filas en snapshot `drive`."""

from sqlalchemy import Column, DateTime, Integer, String, Text, func

from app.core.database import Base


class ClientesDriveExportExcelAuditoria(Base):
    __tablename__ = "clientes_drive_export_excel_auditoria"

    id = Column(Integer, primary_key=True, autoincrement=True)
    exportado_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    usuario_email = Column(String(255), nullable=False)
    modo = Column(String(40), nullable=False)
    filas_count = Column(Integer, nullable=False)
    sheet_rows_json = Column(Text, nullable=True)
