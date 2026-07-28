"""Reclava conciliacion_banco_extracto a serial|fecha|monto y deduplica.

Revision ID: 082_extracto_clave_serial_fecha_monto
Revises: 081_conciliacion_banco_extracto
Create Date: 2026-07-27
"""

from alembic import op


revision = "082_extracto_clave_serial_fecha_monto"
down_revision = "081_conciliacion_banco_extracto"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE conciliacion_banco_extracto
        SET clave_natural =
            COALESCE(NULLIF(TRIM(referencia_norm), ''), TRIM(referencia), '')
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
