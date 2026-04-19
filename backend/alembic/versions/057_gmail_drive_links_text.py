"""pagos_gmail_sync_item / gmail_temporal: drive_link y drive_email_link a TEXT.

Revision ID: 057_gmail_drive_links_text
Revises: 056_auditoria_cliente_alta_desde_drive
Create Date: 2026-04-19
"""

from alembic import op
import sqlalchemy as sa


revision = "057_gmail_drive_links_text"
down_revision = "056_auditoria_cliente_alta_desde_drive"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "pagos_gmail_sync_item",
        "drive_link",
        existing_type=sa.String(500),
        type_=sa.Text(),
        existing_nullable=True,
    )
    op.alter_column(
        "pagos_gmail_sync_item",
        "drive_email_link",
        existing_type=sa.String(500),
        type_=sa.Text(),
        existing_nullable=True,
    )
    op.alter_column(
        "gmail_temporal",
        "drive_link",
        existing_type=sa.String(500),
        type_=sa.Text(),
        existing_nullable=True,
    )
    op.alter_column(
        "gmail_temporal",
        "drive_email_link",
        existing_type=sa.String(500),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "pagos_gmail_sync_item",
        "drive_link",
        existing_type=sa.Text(),
        type_=sa.String(500),
        existing_nullable=True,
    )
    op.alter_column(
        "pagos_gmail_sync_item",
        "drive_email_link",
        existing_type=sa.Text(),
        type_=sa.String(500),
        existing_nullable=True,
    )
    op.alter_column(
        "gmail_temporal",
        "drive_link",
        existing_type=sa.Text(),
        type_=sa.String(500),
        existing_nullable=True,
    )
    op.alter_column(
        "gmail_temporal",
        "drive_email_link",
        existing_type=sa.Text(),
        type_=sa.String(500),
        existing_nullable=True,
    )
