"""Índice parcial pagos_reportados (created_at, id) para cola Cobros.

Revision ID: 066_pagos_reportados_cola_created_at_partial_idx
Revises: 065_pagos_reportados_estado_created_at_idx
Create Date: 2026-04-21

El listado / KPIs de «no validan» recorre sobre todo filas en pendiente, en_revision y
aprobado ordenadas por created_at. Un índice parcial más pequeño que (estado, created_at)
en toda la tabla ayuda al planificador cuando el filtro de estado es IN (cola).

IF NOT EXISTS: seguro en re-ejecución / entornos ya parcheados manualmente.
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import inspect

revision = "066_pagos_reportados_cola_created_at_partial_idx"
down_revision = "065_pagos_reportados_estado_created_at_idx"
branch_labels = None
depends_on = None

INDEX_NAME = "ix_pagos_reportados_cola_created_at_id"


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "pagos_reportados" not in insp.get_table_names():
        return
    existing = {ix["name"] for ix in insp.get_indexes("pagos_reportados")}
    if INDEX_NAME in existing:
        return
    # PostgreSQL y SQLite (tests) aceptan índice parcial con WHERE.
    op.execute(
        f"""
        CREATE INDEX IF NOT EXISTS {INDEX_NAME}
        ON pagos_reportados (created_at, id)
        WHERE estado IN ('pendiente', 'en_revision', 'aprobado')
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "pagos_reportados" not in insp.get_table_names():
        return
    existing = {ix["name"] for ix in insp.get_indexes("pagos_reportados")}
    if INDEX_NAME in existing:
        op.execute(f"DROP INDEX IF EXISTS {INDEX_NAME}")
