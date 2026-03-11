"""Tabla estado_cuenta_codigos para flujo código por email

Revision ID: 011_estado_cuenta_codigos
Revises: 010_pagos_reportados_adjuntos_bd
Create Date: 2026-03

"""
from alembic import op
import sqlalchemy as sa


revision = "011_estado_cuenta_codigos"
down_revision = "010_pagos_reportados_adjuntos_bd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "estado_cuenta_codigos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cedula_normalizada", sa.String(20), nullable=False),
        sa.Column("email", sa.String(100), nullable=False),
        sa.Column("codigo", sa.String(10), nullable=False),
        sa.Column("expira_en", sa.DateTime(timezone=False), nullable=False),
        sa.Column("usado", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("creado_en", sa.DateTime(timezone=False), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_estado_cuenta_codigos_cedula_normalizada", "estado_cuenta_codigos", ["cedula_normalizada"], unique=False)
    op.create_index("ix_estado_cuenta_codigos_id", "estado_cuenta_codigos", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_estado_cuenta_codigos_id", table_name="estado_cuenta_codigos")
    op.drop_index("ix_estado_cuenta_codigos_cedula_normalizada", table_name="estado_cuenta_codigos")
    op.drop_table("estado_cuenta_codigos")
