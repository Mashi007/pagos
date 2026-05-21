"""Migracion en caliente del modulo Cobranzas (Render / BD existente)."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def ensure_cobranzas_schema(engine: Engine) -> None:
    """
    Asegura columnas de bitacora y tabla de adjuntos por nota.
    Idempotente: seguro ejecutar en cada arranque.
    """
    with engine.connect() as conn:
        r = conn.execute(
            text(
                """
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'cobranza_acuerdos'
                """
            )
        )
        if r.fetchone() is None:
            logger.info("[Cobranzas schema] Tabla cobranza_acuerdos no existe; omitiendo ALTER.")
            return

        conn.execute(
            text("ALTER TABLE cobranza_acuerdos ADD COLUMN IF NOT EXISTS mensaje TEXT")
        )
        conn.execute(
            text(
                "ALTER TABLE cobranza_acuerdos ADD COLUMN IF NOT EXISTS cantidad NUMERIC(14, 2)"
            )
        )
        conn.execute(
            text(
                "ALTER TABLE cobranza_acuerdos ADD COLUMN IF NOT EXISTS moneda VARCHAR(10) DEFAULT 'USD'"
            )
        )
        conn.execute(
            text(
                """
                UPDATE cobranza_acuerdos
                SET mensaje = COALESCE(NULLIF(TRIM(mensaje), ''), NULLIF(TRIM(notas), ''), '-'),
                    cantidad = COALESCE(cantidad, monto_compromiso),
                    moneda = COALESCE(NULLIF(TRIM(moneda), ''), 'USD')
                WHERE mensaje IS NULL OR TRIM(mensaje) = ''
                """
            )
        )
        conn.commit()
        logger.info("[Cobranzas schema] Columnas mensaje/cantidad/moneda verificadas.")

    with engine.connect() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS cobranza_nota_adjuntos (
                    id VARCHAR(32) PRIMARY KEY,
                    acuerdo_id INTEGER NOT NULL REFERENCES cobranza_acuerdos(id) ON DELETE CASCADE,
                    nombre_archivo VARCHAR(255),
                    content_type VARCHAR(80) NOT NULL,
                    archivo_data BYTEA NOT NULL,
                    user_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
                    creado_en TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_cobranza_nota_adjuntos_acuerdo
                ON cobranza_nota_adjuntos (acuerdo_id)
                """
            )
        )
        conn.commit()
        logger.info("[Cobranzas schema] Tabla cobranza_nota_adjuntos verificada.")
