"""cedulas_reportar_bs: columna fuente_tasa_cambio (bcv|euro|binance).

El modelo y los endpoints ya usaban este campo; faltaba la migración respecto a 018+052.

Revision ID: 068_cedulas_reportar_bs_fuente_tasa_cambio
Revises: 067_cuotas_prejudicial_vencido_mora_partial_idx
Create Date: 2026-04-22
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "068_cedulas_reportar_bs_fuente_tasa_cambio"
down_revision = "067_cuotas_prejudicial_vencido_mora_partial_idx"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    cols = {c["name"] for c in insp.get_columns("cedulas_reportar_bs")}
    if "fuente_tasa_cambio" in cols:
        return
    op.add_column(
        "cedulas_reportar_bs",
        sa.Column(
            "fuente_tasa_cambio",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'euro'"),
        ),
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    cols = {c["name"] for c in insp.get_columns("cedulas_reportar_bs")}
    if "fuente_tasa_cambio" not in cols:
        return
    op.drop_column("cedulas_reportar_bs", "fuente_tasa_cambio")
