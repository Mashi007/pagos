"""prestamos: caché de comparación ABONOS hoja vs cuotas (notificaciones).

Revision ID: 053_prestamos_abonos_drive_cuotas_cache
Revises: 052_cedulas_reportar_bs_creado_en
Create Date: 2026-04-13
"""

from alembic import op
import sqlalchemy as sa


revision = "053_prestamos_abonos_drive_cuotas_cache"
down_revision = "052_cedulas_reportar_bs_creado_en"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "prestamos",
        sa.Column("abonos_drive_cuotas_cache", sa.JSON(), nullable=True),
    )
    op.add_column(
        "prestamos",
        sa.Column(
            "abonos_drive_cuotas_cache_at",
            sa.DateTime(timezone=False),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("prestamos", "abonos_drive_cuotas_cache_at")
    op.drop_column("prestamos", "abonos_drive_cuotas_cache")
