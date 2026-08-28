"""Migración en caliente Auditoría Email (recibos cola de aprobación)."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

_RECEIPT_COLUMNS = (
    ("banco", "VARCHAR(80)"),
    ("fecha_pago", "VARCHAR(100)"),
    ("numero_referencia", "VARCHAR(200)"),
    ("image_url", "TEXT"),
    ("status", "VARCHAR(24) DEFAULT 'pending'"),
    ("sync_id", "BIGINT"),
    ("sync_item_id", "BIGINT"),
    ("gmail_temporal_id", "BIGINT"),
    ("pago_id", "BIGINT"),
    ("pago_error_id", "BIGINT"),
    ("last_error", "TEXT"),
    ("resolved_at", "TIMESTAMP"),
)


def ensure_auditoria_email_schema(engine: Engine) -> None:
    """Asegura columnas de cola de aprobación en auditoria_email_receipts. Idempotente."""
    with engine.connect() as conn:
        r = conn.execute(
            text(
                """
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'auditoria_email_receipts'
                """
            )
        )
        if r.fetchone() is None:
            logger.info(
                "[AuditoriaEmail schema] Tabla auditoria_email_receipts no existe; omitiendo ALTER."
            )
            return
        for col, ddl in _RECEIPT_COLUMNS:
            conn.execute(
                text(
                    f"ALTER TABLE auditoria_email_receipts "
                    f"ADD COLUMN IF NOT EXISTS {col} {ddl}"
                )
            )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_auditoria_email_receipts_status
                ON auditoria_email_receipts (status)
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE auditoria_email_receipts
                SET status = 'pending'
                WHERE status IS NULL OR TRIM(status) = ''
                """
            )
        )
        conn.commit()
        logger.info("[AuditoriaEmail schema] Columnas cola aprobación verificadas.")
