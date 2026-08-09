"""Migracion en caliente: historial de correos por cliente."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def ensure_clientes_email_historial_schema(engine: Engine) -> None:
    """
    Crea tabla cliente_emails_historial e indices.
    Idempotente: seguro en cada arranque.
    """
    with engine.connect() as conn:
        r = conn.execute(
            text(
                """
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'clientes'
                """
            )
        )
        if r.fetchone() is None:
            logger.info(
                "[Clientes email historial] Tabla clientes no existe; omitiendo."
            )
            return

        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS cliente_emails_historial (
                    id SERIAL PRIMARY KEY,
                    cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
                    cedula VARCHAR(20) NOT NULL,
                    email VARCHAR(150) NOT NULL,
                    email_norm VARCHAR(150) NOT NULL,
                    rol VARCHAR(20) NOT NULL,
                    registrado_en TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    usuario_cambio VARCHAR(50) NULL,
                    CONSTRAINT uq_cliente_emails_historial_cliente_email
                        UNIQUE (cliente_id, email_norm)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_cliente_emails_historial_cliente_id
                ON cliente_emails_historial (cliente_id)
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_cliente_emails_historial_cedula
                ON cliente_emails_historial (cedula)
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_cliente_emails_historial_email_norm
                ON cliente_emails_historial (email_norm)
                """
            )
        )
        conn.commit()
        logger.info("[Clientes email historial] Tabla cliente_emails_historial verificada.")
