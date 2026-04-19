"""Tabla auditoria_cliente_alta_desde_drive (altas desde Drive / CONCILIACIÓN).

Revision ID: 056_auditoria_cliente_alta_desde_drive
Revises: 055_pagos_gmail_sync_run_summary
Create Date: 2026-04-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "056_auditoria_cliente_alta_desde_drive"
down_revision = "055_pagos_gmail_sync_run_summary"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "auditoria_cliente_alta_desde_drive" in insp.get_table_names():
        return
    op.create_table(
        "auditoria_cliente_alta_desde_drive",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("batch_id", sa.String(length=40), nullable=False),
        sa.Column("sheet_row_number", sa.Integer(), nullable=False),
        sa.Column("cedula", sa.String(length=32), nullable=False),
        sa.Column("nombres", sa.Text(), nullable=True),
        sa.Column("telefono", sa.String(length=120), nullable=True),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("comentario", sa.Text(), nullable=True),
        sa.Column("usuario_email", sa.String(length=200), nullable=False),
        sa.Column("estado", sa.String(length=32), nullable=False),
        sa.Column("detalle_error", sa.Text(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_auditoria_cliente_alta_desde_drive_batch_id",
        "auditoria_cliente_alta_desde_drive",
        ["batch_id"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "auditoria_cliente_alta_desde_drive" not in insp.get_table_names():
        return
    op.drop_index("ix_auditoria_cliente_alta_desde_drive_batch_id", table_name="auditoria_cliente_alta_desde_drive")
    op.drop_table("auditoria_cliente_alta_desde_drive")
