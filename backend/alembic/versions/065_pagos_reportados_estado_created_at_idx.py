"""Índice pagos_reportados (estado, created_at) para listados Cobros ordenados por fecha.

Revision ID: 065_pagos_reportados_estado_created_at_idx
Revises: 064_pagos_gmail_trazabilidad_ids_evento
Create Date: 2026-04-20
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import inspect

revision = "065_pagos_reportados_estado_created_at_idx"
down_revision = "064_pagos_gmail_trazabilidad_ids_evento"
branch_labels = None
depends_on = None

INDEX_NAME = "ix_pagos_reportados_estado_created_at"


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "pagos_reportados" not in insp.get_table_names():
        return
    existing = {ix["name"] for ix in insp.get_indexes("pagos_reportados")}
    if INDEX_NAME in existing:
        return
    op.create_index(
        INDEX_NAME,
        "pagos_reportados",
        ["estado", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "pagos_reportados" not in insp.get_table_names():
        return
    existing = {ix["name"] for ix in insp.get_indexes("pagos_reportados")}
    if INDEX_NAME in existing:
        op.drop_index(INDEX_NAME, table_name="pagos_reportados")
