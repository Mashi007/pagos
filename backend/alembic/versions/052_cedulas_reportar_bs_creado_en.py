"""cedulas_reportar_bs: fecha de alta para listar y paginar (más reciente primero).

Revision ID: 052_cedulas_reportar_bs_creado_en
Revises: 051_revision_manual_solicitudes_reapertura
Create Date: 2026-04-10
"""

from alembic import op
import sqlalchemy as sa


revision = "052_cedulas_reportar_bs_creado_en"
down_revision = "051_revision_manual_solicitudes_reapertura"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cedulas_reportar_bs",
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        """
        UPDATE cedulas_reportar_bs
        SET creado_en = TIMESTAMPTZ '1970-01-01T00:00:00+00:00'
        WHERE creado_en IS NULL
        """
    )
    op.alter_column(
        "cedulas_reportar_bs",
        "creado_en",
        nullable=False,
        server_default=sa.text("now()"),
    )


def downgrade() -> None:
    op.drop_column("cedulas_reportar_bs", "creado_en")
