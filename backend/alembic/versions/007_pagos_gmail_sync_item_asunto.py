"""Add asunto column to pagos_gmail_sync_item (columna A = Asunto en Excel)

Revision ID: 007_asunto
Revises: 006_fix_cliente_fecha_registro_default
Create Date: 2026-03

Columna A pasa de 'Correo Origen' a 'Asunto'; se guarda el asunto del correo.
"""
from alembic import op
import sqlalchemy as sa


revision = "007_asunto"
down_revision = "006_fix_cliente_fecha_registro_default"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pagos_gmail_sync_item",
        sa.Column("asunto", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pagos_gmail_sync_item", "asunto")
