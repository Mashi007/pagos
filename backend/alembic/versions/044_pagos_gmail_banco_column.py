"""Add banco to pagos_gmail_sync_item and gmail_temporal (Excel: Mercantil / BNC).

Revision ID: 044_pagos_gmail_banco
Revises: 043_pagos_gmail_correos_revision
Create Date: 2026-04-02

"""
from alembic import op
import sqlalchemy as sa


revision = "044_pagos_gmail_banco"
down_revision = "043_pagos_gmail_correos_revision"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pagos_gmail_sync_item",
        sa.Column("banco", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "gmail_temporal",
        sa.Column("banco", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("gmail_temporal", "banco")
    op.drop_column("pagos_gmail_sync_item", "banco")
