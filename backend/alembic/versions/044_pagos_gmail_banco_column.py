"""Add banco to pagos_gmail_sync_item and gmail_temporal (Excel: Mercantil / BNC).

Revision ID: 044_pagos_gmail_banco
Revises: 043_pagos_gmail_correos_revision
Create Date: 2026-04-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "044_pagos_gmail_banco"
down_revision = "043_pagos_gmail_correos_revision"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    cols_item = {c["name"] for c in insp.get_columns("pagos_gmail_sync_item")}
    if "banco" not in cols_item:
        op.add_column(
            "pagos_gmail_sync_item",
            sa.Column("banco", sa.String(length=50), nullable=True),
        )
    cols_tmp = {c["name"] for c in insp.get_columns("gmail_temporal")}
    if "banco" not in cols_tmp:
        op.add_column(
            "gmail_temporal",
            sa.Column("banco", sa.String(length=50), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    cols_tmp = {c["name"] for c in insp.get_columns("gmail_temporal")}
    if "banco" in cols_tmp:
        op.drop_column("gmail_temporal", "banco")
    cols_item = {c["name"] for c in insp.get_columns("pagos_gmail_sync_item")}
    if "banco" in cols_item:
        op.drop_column("pagos_gmail_sync_item", "banco")
