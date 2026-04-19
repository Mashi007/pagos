# -*- coding: utf-8 -*-
"""
Eventos de auditoría previos a fila `pagos_gmail_sync_item` (rechazo Gemini, dedupe, remitente, etc.).
Permite trazar hilos Gmail sin depender solo de logs.
"""
from sqlalchemy import Column, ForeignKey, Integer, String, Text, DateTime
from sqlalchemy.sql import func

from app.core.database import Base


class PagosGmailPipelineEvento(Base):
    __tablename__ = "pagos_gmail_pipeline_evento"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sync_id = Column(
        Integer,
        ForeignKey("pagos_gmail_sync.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    gmail_message_id = Column(String(100), nullable=False, index=True)
    gmail_thread_id = Column(String(100), nullable=True, index=True)
    sha256_hex = Column(String(64), nullable=True)
    filename = Column(String(500), nullable=True)
    motivo = Column(String(64), nullable=False, index=True)
    detalle = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
