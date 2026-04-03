"""Tabla adjunto_fijo_cobranza_documento: PDFs de pestana Documentos PDF anexos en BYTEA (persistente en Render).

Revision ID: 046_adjunto_fijo_cobranza_documento_bd
Revises: 045_pagos_link_comprobante
Create Date: 2026-04-03

"""
from alembic import op
import sqlalchemy as sa


revision = "046_adjunto_fijo_cobranza_documento_bd"
down_revision = "045_pagos_link_comprobante"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "adjunto_fijo_cobranza_documento",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tipo_caso", sa.String(length=32), nullable=False),
        sa.Column("nombre_archivo", sa.String(length=512), nullable=False),
        sa.Column("pdf_data", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_adjunto_fijo_cobranza_documento_tipo_caso"),
        "adjunto_fijo_cobranza_documento",
        ["tipo_caso"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_adjunto_fijo_cobranza_documento_tipo_caso"),
        table_name="adjunto_fijo_cobranza_documento",
    )
    op.drop_table("adjunto_fijo_cobranza_documento")
