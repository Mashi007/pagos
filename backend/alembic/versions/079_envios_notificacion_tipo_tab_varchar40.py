"""Widen envios_notificacion.tipo_tab for d_2_antes_vencimiento (21 chars).

Revision ID: 079_envios_notificacion_tipo_tab_varchar40
Revises: 078_disable_retraso_snapshot_trigger_hot_path
Create Date: 2026-07-21

``d_2_antes_vencimiento`` has 21 characters; column was VARCHAR(20), so failed
SMTP rows could not be persisted (StringDataRightTruncation).
"""

from alembic import op


revision = "079_envios_notificacion_tipo_tab_varchar40"
down_revision = "078_disable_retraso_snapshot_trigger_hot_path"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE envios_notificacion ALTER COLUMN tipo_tab TYPE VARCHAR(40)"
    )


def downgrade() -> None:
    # Truncate only if any value exceeds 20 before shrinking (safe no-op if already short).
    op.execute(
        """
        UPDATE envios_notificacion
        SET tipo_tab = LEFT(tipo_tab, 20)
        WHERE char_length(tipo_tab) > 20
        """
    )
    op.execute(
        "ALTER TABLE envios_notificacion ALTER COLUMN tipo_tab TYPE VARCHAR(20)"
    )
