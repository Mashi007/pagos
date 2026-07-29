"""Reclava conciliacion_banco_extracto a banco|serial|fecha|monto.

Revision ID: 084_extracto_clave_banco
Revises: 083_cobranza_universo_cedulas
Create Date: 2026-07-29
"""

from alembic import op


revision = "084_extracto_clave_banco"
down_revision = "083_cobranza_universo_cedulas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE conciliacion_banco_extracto
        SET clave_natural =
            TRIM(banco)
            || '|' || COALESCE(NULLIF(TRIM(referencia_norm), ''), TRIM(referencia), '')
            || '|' || COALESCE(to_char(fecha, 'YYYY-MM-DD'), '')
            || '|' || CASE
                WHEN monto IS NULL THEN ''
                ELSE TRIM(to_char(monto, 'FM999999999990.00'))
            END
        """
    )
    op.execute(
        """
        DELETE FROM conciliacion_banco_extracto a
        USING conciliacion_banco_extracto b
        WHERE a.clave_natural = b.clave_natural
          AND a.id < b.id
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_conciliacion_banco_extracto_clave "
        "ON conciliacion_banco_extracto (clave_natural)"
    )


def downgrade() -> None:
    pass
