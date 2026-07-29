"""Universo de cedulas Excel para analisis de cobranzas (buckets mora).

Revision ID: 083_cobranza_universo_cedulas
Revises: 082_extracto_clave_serial_fecha_monto
Create Date: 2026-07-28
"""

from alembic import op
import sqlalchemy as sa


revision = "083_cobranza_universo_cedulas"
down_revision = "082_extracto_clave_serial_fecha_monto"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cobranza_universo_cedulas",
        sa.Column("cedula", sa.String(20), nullable=False),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("cedula"),
    )
    op.create_table(
        "cobranza_universo_desempeno_diario",
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("bucket", sa.String(10), nullable=False),
        sa.Column("monto_usd", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("cantidad_prestamos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("fecha", "bucket"),
    )


def downgrade() -> None:
    op.drop_table("cobranza_universo_desempeno_diario")
    op.drop_table("cobranza_universo_cedulas")
