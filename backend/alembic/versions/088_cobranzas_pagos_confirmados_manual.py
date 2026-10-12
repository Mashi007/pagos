"""Tabla override manual Pagos confirmados (Cobranzas).

Revision ID: 088_cobranzas_pagos_confirmados_manual
Revises: 087_clientes_fecha_registro_default_now
"""
from alembic import op
import sqlalchemy as sa

revision = "088_cobranzas_pagos_confirmados_manual"
down_revision = "087_clientes_fecha_registro_default_now"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cobranzas_pagos_confirmados_manual",
        sa.Column("fecha_lectura", sa.Date(), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("monto_usd", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_by", sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint("fecha_lectura"),
    )


def downgrade() -> None:
    op.drop_table("cobranzas_pagos_confirmados_manual")
