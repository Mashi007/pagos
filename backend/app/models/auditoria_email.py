"""
Submódulo Auditoría → Email (buzón cobranza@).
Tablas: jobs de escaneo, mensajes ingeridos y recibos extraídos.
"""
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

from app.core.database import Base


def _json_type():
    return JSON().with_variant(JSONB, "postgresql")


class AuditoriaEmailScan(Base):
    __tablename__ = "auditoria_email_scans"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    mode = Column(String(16), nullable=False, server_default=text("'single'"))
    status = Column(String(24), nullable=False, index=True, server_default=text("'pending'"))
    source = Column(String(16), nullable=False, server_default=text("'demo'"))
    criteria_json = Column(_json_type(), nullable=False, server_default=text("'{}'"))
    pipeline_ids_json = Column(_json_type(), nullable=False, server_default=text("'[]'"))
    lot_size = Column(Integer, nullable=False, server_default=text("250"))
    max_messages = Column(Integer, nullable=False, server_default=text("100"))
    gmail_query = Column(Text, nullable=True)
    page_token = Column(Text, nullable=True)
    processed_total = Column(Integer, nullable=False, server_default=text("0"))
    listed_total = Column(Integer, nullable=False, server_default=text("0"))
    rejected_total = Column(Integer, nullable=False, server_default=text("0"))
    lots_done = Column(Integer, nullable=False, server_default=text("0"))
    last_error = Column(Text, nullable=True)
    created_by = Column(String(150), nullable=True)
    created_at = Column(
        DateTime(timezone=False),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        index=True,
    )
    updated_at = Column(
        DateTime(timezone=False),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    finished_at = Column(DateTime(timezone=False), nullable=True)


class AuditoriaEmailMessage(Base):
    __tablename__ = "auditoria_email_messages"
    __table_args__ = (
        UniqueConstraint("gmail_message_id", name="uq_auditoria_email_gmail_message_id"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    scan_id = Column(BigInteger, nullable=True, index=True)
    gmail_message_id = Column(String(64), nullable=False, index=True)
    gmail_thread_id = Column(String(64), nullable=True)
    source = Column(String(16), nullable=False, server_default=text("'demo'"))
    from_email = Column(String(255), nullable=True, index=True)
    from_name = Column(String(255), nullable=True)
    subject = Column(String(700), nullable=True)
    snippet = Column(Text, nullable=True)
    internal_date = Column(DateTime(timezone=False), nullable=True, index=True)
    has_attachment = Column(Boolean, nullable=False, server_default=text("false"))
    attachment_types = Column(_json_type(), nullable=False, server_default=text("'[]'"))
    attachment_max_kb = Column(Integer, nullable=True)
    filename_joined = Column(Text, nullable=True)
    label_ids = Column(_json_type(), nullable=False, server_default=text("'[]'"))
    classify = Column(String(40), nullable=True, index=True)
    route = Column(String(40), nullable=True, index=True)
    sla_hours = Column(Float, nullable=True)
    riesgo = Column(String(24), nullable=True, index=True)
    evidencia = Column(String(24), nullable=True)
    extract_json = Column(_json_type(), nullable=True)
    ocr_json = Column(_json_type(), nullable=True)
    pipelines_json = Column(_json_type(), nullable=True)
    ingested_at = Column(
        DateTime(timezone=False),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        index=True,
    )


class AuditoriaEmailReceipt(Base):
    __tablename__ = "auditoria_email_receipts"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    message_id = Column(BigInteger, nullable=False, index=True)
    gmail_message_id = Column(String(64), nullable=False, index=True)
    filename = Column(String(400), nullable=True)
    mime_type = Column(String(120), nullable=True)
    size_kb = Column(Integer, nullable=True)
    cedula = Column(String(32), nullable=True, index=True)
    monto = Column(Float, nullable=True)
    route = Column(String(40), nullable=True, index=True)
    ocr_status = Column(String(24), nullable=False, server_default=text("'heuristica'"))
    created_at = Column(
        DateTime(timezone=False),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
