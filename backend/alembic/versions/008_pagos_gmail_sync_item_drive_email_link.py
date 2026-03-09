"""Add drive_email_link to pagos_gmail_sync_item (link al .eml del correo en Drive)

Revision ID: 008_drive_email_link
Revises: 007_asunto
Create Date: 2026-03

Permite abrir el correo completo desde el Excel para verificación.
"""
from alembic import op
import sqlalchemy as sa


revision = "008_drive_email_link"
down_revision = "007_asunto"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pagos_gmail_sync_item",
        sa.Column("drive_email_link", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pagos_gmail_sync_item", "drive_email_link")
