"""Add monto_capital, monto_interes, total_pagado, dias_morosidad to cuotas

Revision ID: 005_add_cuotas_columns
Revises: 004_add_dashboard_indexes
Create Date: 2026-03-05

Fixes ProgrammingError on GET /prestamos/{id}/cuotas:
  column cuotas.monto_capital does not exist

The Cuota model expects these columns; production DB was missing them.
"""
from alembic import op
import sqlalchemy as sa


revision = "005_add_cuotas_columns"
down_revision = "004_add_dashboard_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add columns expected by app.models.cuota.Cuota (B3 / amortization)
    op.add_column(
        "cuotas",
        sa.Column("monto_capital", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "cuotas",
        sa.Column("monto_interes", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "cuotas",
        sa.Column("total_pagado", sa.Numeric(14, 2), nullable=True),
    )
    op.add_column(
        "cuotas",
        sa.Column("dias_morosidad", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("cuotas", "dias_morosidad")
    op.drop_column("cuotas", "total_pagado")
    op.drop_column("cuotas", "monto_interes")
    op.drop_column("cuotas", "monto_capital")
