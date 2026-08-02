"""Tabla universo cedulas informe Aseguradora.

Revision ID: 085_aseguradora_universo
Revises: 084_extracto_clave_banco
Create Date: 2026-08-02
"""

from alembic import op
import sqlalchemy as sa


revision = "085_aseguradora_universo"
down_revision = "084_extracto_clave_banco"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "aseguradora_universo_cedulas",
        sa.Column("cedula", sa.String(length=20), primary_key=True),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("aseguradora_universo_cedulas")
