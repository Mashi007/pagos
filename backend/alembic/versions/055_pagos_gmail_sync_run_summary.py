"""pagos_gmail_sync: run_summary JSON (diagnóstico última corrida Gmail).

Revision ID: 055_pagos_gmail_sync_run_summary
Revises: 054_prestamos_fecha_entrega_q_aprobacion_cache
Create Date: 2026-04-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "055_pagos_gmail_sync_run_summary"
down_revision = "054_prestamos_fecha_entrega_q_aprobacion_cache"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    cols = {c["name"] for c in insp.get_columns("pagos_gmail_sync")}
    if "run_summary" in cols:
        return
    op.add_column(
        "pagos_gmail_sync",
        sa.Column("run_summary", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    cols = {c["name"] for c in insp.get_columns("pagos_gmail_sync")}
    if "run_summary" not in cols:
        return
    op.drop_column("pagos_gmail_sync", "run_summary")
