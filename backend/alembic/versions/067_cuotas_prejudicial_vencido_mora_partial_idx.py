"""Índice parcial cuotas para listado prejudicial (VENCIDO/MORA, sin pagar, saldo > tol).

Revision ID: 067_cuotas_prejudicial_vencido_mora_partial_idx
Revises: 066_pagos_reportados_cola_created_at_partial_idx
Create Date: 2026-04-21

`build_prejudicial_items` agrupa por titular (prestamo) con:
  fecha_pago IS NULL, estado IN (VENCIDO, MORA), fecha_vencimiento < :hoy,
  (monto_cuota - total_pagado) > tolerancia, préstamo no liquidado/desistimiento.

Este índice reduce el coste del GROUP BY / segunda consulta sin alterar resultados.
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import inspect

revision = "067_cuotas_prejudicial_vencido_mora_partial_idx"
down_revision = "066_pagos_reportados_cola_created_at_partial_idx"
branch_labels = None
depends_on = None

INDEX_NAME = "ix_cuotas_prejudicial_vencido_mora_prestamo_fv"


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "cuotas" not in insp.get_table_names():
        return
    existing = {ix["name"] for ix in insp.get_indexes("cuotas")}
    if INDEX_NAME in existing:
        return
    op.execute(
        f"""
        CREATE INDEX IF NOT EXISTS {INDEX_NAME}
        ON cuotas (prestamo_id, fecha_vencimiento)
        WHERE fecha_pago IS NULL
          AND estado IN ('VENCIDO', 'MORA')
          AND (COALESCE(monto_cuota, 0) - COALESCE(total_pagado, 0)) > 0.01
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "cuotas" not in insp.get_table_names():
        return
    existing = {ix["name"] for ix in insp.get_indexes("cuotas")}
    if INDEX_NAME in existing:
        op.execute(f"DROP INDEX IF EXISTS {INDEX_NAME}")
