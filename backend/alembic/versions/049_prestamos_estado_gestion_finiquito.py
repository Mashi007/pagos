"""prestamos: columna estado_gestion_finiquito (ANTIGUO, EN_PROCESO, TERMINADO).

Revision ID: 049_prestamos_estado_gestion_finiquito
Revises: 048_fix_retraso_snapshot_trigger_refresh_in_transaction
Create Date: 2026-04-05

Refleja en el préstamo la fase finiquito para consulta de cualquier usuario.
Backfill desde finiquito_casos existentes.
"""

from alembic import op
import sqlalchemy as sa


revision = "049_prestamos_estado_gestion_finiquito"
down_revision = "048_fix_retraso_snapshot_trigger_refresh_in_transaction"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "prestamos",
        sa.Column(
            "estado_gestion_finiquito",
            sa.String(length=32),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_prestamos_estado_gestion_finiquito",
        "prestamos",
        ["estado_gestion_finiquito"],
        unique=False,
    )
    op.execute(
        """
        UPDATE prestamos p
        SET estado_gestion_finiquito = c.estado
        FROM finiquito_casos c
        WHERE c.prestamo_id = p.id
          AND UPPER(TRIM(c.estado)) IN ('ANTIGUO', 'EN_PROCESO', 'TERMINADO');
        """
    )


def downgrade() -> None:
    op.drop_index("ix_prestamos_estado_gestion_finiquito", table_name="prestamos")
    op.drop_column("prestamos", "estado_gestion_finiquito")
