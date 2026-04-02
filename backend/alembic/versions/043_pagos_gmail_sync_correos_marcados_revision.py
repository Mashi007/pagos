"""Add correos_marcados_revision to pagos_gmail_sync (metricas pipeline manual Gmail).

Revision ID: 043_pagos_gmail_correos_revision
Revises: 042_cobros_publico_codigos
Create Date: 2026-04-02

"""
from alembic import op
import sqlalchemy as sa


revision = "043_pagos_gmail_correos_revision"
down_revision = "042_cobros_publico_codigos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pagos_gmail_sync",
        sa.Column("correos_marcados_revision", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("pagos_gmail_sync", "correos_marcados_revision")
