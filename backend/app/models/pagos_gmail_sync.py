"""
Modelos para el pipeline Gmail -> Drive -> Gemini -> Sheets (módulo Pagos).
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.core.database import Base


class PagosGmailSync(Base):
    __tablename__ = "pagos_gmail_sync"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    started_at = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
    finished_at = Column(DateTime(timezone=False), nullable=True)
    status = Column(String(20), nullable=False, default="running")  # running | success | error
    emails_processed = Column(Integer, nullable=False, default=0)
    files_processed = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)


class PagosGmailSyncItem(Base):
    __tablename__ = "pagos_gmail_sync_item"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sync_id = Column(Integer, ForeignKey("pagos_gmail_sync.id", ondelete="CASCADE"), nullable=False, index=True)
    correo_origen = Column(String(255), nullable=False)  # remitente; se mantiene por compatibilidad
    asunto = Column(String(500), nullable=True)  # Asunto del correo (columna A en Excel)
    fecha_pago = Column(String(100), nullable=True)
    cedula = Column(String(50), nullable=True)
    monto = Column(String(100), nullable=True)
    numero_referencia = Column(String(200), nullable=True)
    drive_file_id = Column(String(100), nullable=True)
    drive_link = Column(String(500), nullable=True)
    sheet_name = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
