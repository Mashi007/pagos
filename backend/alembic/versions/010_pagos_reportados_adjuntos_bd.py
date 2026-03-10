"""Almacenar comprobante y recibo PDF en BD (BYTEA)

Revision ID: 010_pagos_reportados_adjuntos_bd
Revises: 009_pagos_reportados
Create Date: 2026-03

Añade columnas comprobante, comprobante_nombre, comprobante_tipo, recibo_pdf.
ruta_comprobante pasa a nullable.
"""
from alembic import op
import sqlalchemy as sa


revision = "010_pagos_reportados_adjuntos_bd"
down_revision = "009_pagos_reportados"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pagos_reportados", sa.Column("comprobante", sa.LargeBinary(), nullable=True))
    op.add_column("pagos_reportados", sa.Column("comprobante_nombre", sa.String(255), nullable=True))
    op.add_column("pagos_reportados", sa.Column("comprobante_tipo", sa.String(100), nullable=True))
    op.add_column("pagos_reportados", sa.Column("recibo_pdf", sa.LargeBinary(), nullable=True))
    op.alter_column(
        "pagos_reportados",
        "ruta_comprobante",
        existing_type=sa.String(512),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "pagos_reportados",
        "ruta_comprobante",
        existing_type=sa.String(512),
        nullable=False,
    )
    op.drop_column("pagos_reportados", "recibo_pdf")
    op.drop_column("pagos_reportados", "comprobante_tipo")
    op.drop_column("pagos_reportados", "comprobante_nombre")
    op.drop_column("pagos_reportados", "comprobante")
