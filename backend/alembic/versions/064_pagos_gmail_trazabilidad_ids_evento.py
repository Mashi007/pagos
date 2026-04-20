"""Gmail: ids mensaje/hilo en sync_item y temporal; eventos pipeline; gemini_model en resumen (app).

Revision ID: 064_pagos_gmail_trazabilidad_ids_evento
Revises: 063_pagos_gmail_traza_plantilla_fmt_nr
Create Date: 2026-04-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "064_pagos_gmail_trazabilidad_ids_evento"
down_revision = "063_pagos_gmail_traza_plantilla_fmt_nr"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    if "pagos_gmail_sync_item" in insp.get_table_names():
        cols_item = {c["name"] for c in insp.get_columns("pagos_gmail_sync_item")}
        if "gmail_message_id" not in cols_item:
            op.add_column(
                "pagos_gmail_sync_item",
                sa.Column("gmail_message_id", sa.String(length=100), nullable=True),
            )
        if "gmail_thread_id" not in cols_item:
            op.add_column(
                "pagos_gmail_sync_item",
                sa.Column("gmail_thread_id", sa.String(length=100), nullable=True),
            )
        idx_names = {ix["name"] for ix in inspect(bind).get_indexes("pagos_gmail_sync_item")}
        if "ix_pagos_gmail_sync_item_gmail_message_id" not in idx_names:
            op.create_index(
                "ix_pagos_gmail_sync_item_gmail_message_id",
                "pagos_gmail_sync_item",
                ["gmail_message_id"],
                unique=False,
            )

    if "gmail_temporal" in insp.get_table_names():
        cols_tmp = {c["name"] for c in insp.get_columns("gmail_temporal")}
        if "gmail_message_id" not in cols_tmp:
            op.add_column(
                "gmail_temporal",
                sa.Column("gmail_message_id", sa.String(length=100), nullable=True),
            )
        if "gmail_thread_id" not in cols_tmp:
            op.add_column(
                "gmail_temporal",
                sa.Column("gmail_thread_id", sa.String(length=100), nullable=True),
            )

    if "pagos_gmail_pipeline_evento" not in insp.get_table_names():
        op.create_table(
            "pagos_gmail_pipeline_evento",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("sync_id", sa.Integer(), nullable=True),
            sa.Column("gmail_message_id", sa.String(length=100), nullable=False),
            sa.Column("gmail_thread_id", sa.String(length=100), nullable=True),
            sa.Column("sha256_hex", sa.String(length=64), nullable=True),
            sa.Column("filename", sa.String(length=500), nullable=True),
            sa.Column("motivo", sa.String(length=64), nullable=False),
            sa.Column("detalle", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(
                ["sync_id"],
                ["pagos_gmail_sync.id"],
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_pagos_gmail_pipeline_evento_sync_id",
            "pagos_gmail_pipeline_evento",
            ["sync_id"],
            unique=False,
        )
        op.create_index(
            "ix_pagos_gmail_pipeline_evento_gmail_message_id",
            "pagos_gmail_pipeline_evento",
            ["gmail_message_id"],
            unique=False,
        )
        op.create_index(
            "ix_pagos_gmail_pipeline_evento_gmail_thread_id",
            "pagos_gmail_pipeline_evento",
            ["gmail_thread_id"],
            unique=False,
        )
        op.create_index(
            "ix_pagos_gmail_pipeline_evento_motivo",
            "pagos_gmail_pipeline_evento",
            ["motivo"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    if "pagos_gmail_pipeline_evento" in insp.get_table_names():
        op.drop_index("ix_pagos_gmail_pipeline_evento_motivo", table_name="pagos_gmail_pipeline_evento")
        op.drop_index("ix_pagos_gmail_pipeline_evento_gmail_thread_id", table_name="pagos_gmail_pipeline_evento")
        op.drop_index("ix_pagos_gmail_pipeline_evento_gmail_message_id", table_name="pagos_gmail_pipeline_evento")
        op.drop_index("ix_pagos_gmail_pipeline_evento_sync_id", table_name="pagos_gmail_pipeline_evento")
        op.drop_table("pagos_gmail_pipeline_evento")

    if "gmail_temporal" in insp.get_table_names():
        cols_tmp = {c["name"] for c in insp.get_columns("gmail_temporal")}
        if "gmail_thread_id" in cols_tmp:
            op.drop_column("gmail_temporal", "gmail_thread_id")
        if "gmail_message_id" in cols_tmp:
            op.drop_column("gmail_temporal", "gmail_message_id")

    if "pagos_gmail_sync_item" in insp.get_table_names():
        idx_names = {ix["name"] for ix in insp.get_indexes("pagos_gmail_sync_item")}
        if "ix_pagos_gmail_sync_item_gmail_message_id" in idx_names:
            op.drop_index("ix_pagos_gmail_sync_item_gmail_message_id", table_name="pagos_gmail_sync_item")
        cols_item = {c["name"] for c in insp.get_columns("pagos_gmail_sync_item")}
        if "gmail_thread_id" in cols_item:
            op.drop_column("pagos_gmail_sync_item", "gmail_thread_id")
        if "gmail_message_id" in cols_item:
            op.drop_column("pagos_gmail_sync_item", "gmail_message_id")
