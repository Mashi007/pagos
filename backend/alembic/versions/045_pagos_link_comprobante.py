"""Add link_comprobante to pagos (URL foto/comprobante desde Excel Gmail u otros).

Revision ID: 045_pagos_link_comprobante
Revises: 044_pagos_gmail_banco
Create Date: 2026-04-02

"""
from alembic import op
import sqlalchemy as sa


revision = "045_pagos_link_comprobante"
down_revision = "044_pagos_gmail_banco"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pagos",
        sa.Column("link_comprobante", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pagos", "link_comprobante")
