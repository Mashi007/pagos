"""Tabla cedulas_reportar_bs: cédulas que pueden reportar en Bs (rapicredit-cobros / infopagos).

Revision ID: 018_cedulas_reportar_bs
Revises: 017_datos_importados_conerrores
Create Date: 2026-03-18

"""
from alembic import op
import sqlalchemy as sa

revision = "018_cedulas_reportar_bs"
down_revision = "017_datos_importados_conerrores"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cedulas_reportar_bs",
        sa.Column("cedula", sa.String(20), nullable=False),
        sa.PrimaryKeyConstraint("cedula"),
    )
    op.create_index("ix_cedulas_reportar_bs_cedula", "cedulas_reportar_bs", ["cedula"])


def downgrade() -> None:
    op.drop_index("ix_cedulas_reportar_bs_cedula", "cedulas_reportar_bs")
    op.drop_table("cedulas_reportar_bs")
