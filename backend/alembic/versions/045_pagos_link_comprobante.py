"""Add link_comprobante to pagos (URL foto/comprobante desde Excel Gmail u otros).

Revision ID: 045_pagos_link_comprobante
Revises: 044_pagos_gmail_banco
Create Date: 2026-04-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "045_pagos_link_comprobante"
down_revision = "044_pagos_gmail_banco"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    cols = {c["name"] for c in insp.get_columns("pagos")}
    if "link_comprobante" in cols:
        return
    op.add_column(
        "pagos",
        sa.Column("link_comprobante", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    cols = {c["name"] for c in insp.get_columns("pagos")}
    if "link_comprobante" not in cols:
        return
    op.drop_column("pagos", "link_comprobante")
