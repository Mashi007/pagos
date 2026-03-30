"""pagos_reportados.canal_ingreso: Infopagos vs formulario publico (misma cola).

Revision ID: 031_pagos_reportados_canal_ingreso
Revises: 030_auditoria_cartera_revision
Create Date: 2026-03-30
"""

from alembic import op
import sqlalchemy as sa


revision = "031_pagos_reportados_canal_ingreso"
down_revision = "030_auditoria_cartera_revision"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pagos_reportados",
        sa.Column("canal_ingreso", sa.String(length=32), nullable=True),
    )
    op.create_index(
        "ix_pagos_reportados_canal_ingreso",
        "pagos_reportados",
        ["canal_ingreso"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_pagos_reportados_canal_ingreso", table_name="pagos_reportados")
    op.drop_column("pagos_reportados", "canal_ingreso")
