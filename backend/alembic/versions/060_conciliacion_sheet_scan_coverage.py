"""Metadatos de cobertura de escaneo Drive (última fila + cola Google).

Revision ID: 060_conciliacion_sheet_scan_coverage
Revises: 059_pagos_gmail_abcd_cuotas_traza
Create Date: 2026-05-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "060_conciliacion_sheet_scan_coverage"
down_revision = "059_pagos_gmail_abcd_cuotas_traza"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "conciliacion_sheet_meta" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("conciliacion_sheet_meta")}
    if "last_data_sheet_row_number" not in cols:
        op.add_column(
            "conciliacion_sheet_meta",
            sa.Column("last_data_sheet_row_number", sa.Integer(), nullable=True),
        )
    if "google_tail_row_number" not in cols:
        op.add_column(
            "conciliacion_sheet_meta",
            sa.Column("google_tail_row_number", sa.Integer(), nullable=True),
        )
    if "google_tail_row_probed_at" not in cols:
        op.add_column(
            "conciliacion_sheet_meta",
            sa.Column("google_tail_row_probed_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "conciliacion_sheet_meta" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("conciliacion_sheet_meta")}
    if "google_tail_row_probed_at" in cols:
        op.drop_column("conciliacion_sheet_meta", "google_tail_row_probed_at")
    if "google_tail_row_number" in cols:
        op.drop_column("conciliacion_sheet_meta", "google_tail_row_number")
    if "last_data_sheet_row_number" in cols:
        op.drop_column("conciliacion_sheet_meta", "last_data_sheet_row_number")
