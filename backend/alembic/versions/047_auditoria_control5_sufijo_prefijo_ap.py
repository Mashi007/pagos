"""Ampliar sufijo control 5 Visto: letra A/P + 4 digitos (mismo prestamo vs otro prestamo).

Revision ID: 047_auditoria_control5_sufijo_prefijo_ap
Revises: 046_adjunto_fijo_cobranza_documento_bd
Create Date: 2026-04-02

"""
from alembic import op
import sqlalchemy as sa


revision = "047_auditoria_control5_sufijo_prefijo_ap"
down_revision = "046_adjunto_fijo_cobranza_documento_bd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "auditoria_pago_control5_visto",
        "sufijo_cuatro_digitos",
        existing_type=sa.CHAR(length=4),
        type_=sa.String(length=8),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "auditoria_pago_control5_visto",
        "sufijo_cuatro_digitos",
        existing_type=sa.String(length=8),
        type_=sa.CHAR(length=4),
        existing_nullable=False,
    )
