"""Ampliar plantilla_fmt en traza Gmail (NR = 2 caracteres).

Revision ID: 063_pagos_gmail_traza_plantilla_fmt_nr
Revises: 062_recibos_email_envio
Create Date: 2026-04-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "063_pagos_gmail_traza_plantilla_fmt_nr"
down_revision = "062_recibos_email_envio"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "pagos_gmail_abcd_cuotas_traza" not in insp.get_table_names():
        return
    op.alter_column(
        "pagos_gmail_abcd_cuotas_traza",
        "plantilla_fmt",
        existing_type=sa.String(length=1),
        type_=sa.String(length=4),
        existing_nullable=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "pagos_gmail_abcd_cuotas_traza" not in insp.get_table_names():
        return
    op.alter_column(
        "pagos_gmail_abcd_cuotas_traza",
        "plantilla_fmt",
        existing_type=sa.String(length=4),
        type_=sa.String(length=1),
        existing_nullable=False,
    )
