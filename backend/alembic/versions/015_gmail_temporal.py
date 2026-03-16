"""Tabla gmail_temporal para descarga Excel: datos se vacian al descargar.

Revision ID: 015_gmail_temporal
Revises: 014_crm_campana_programado
Create Date: 2026-03

Cada procesamiento Gmail inserta en gmail_temporal a continuacion del ultimo.
GET /pagos/gmail/download-excel-temporal genera Excel desde esta tabla y luego la vacia (TRUNCATE).
"""
from alembic import op
import sqlalchemy as sa

revision = "015_gmail_temporal"
down_revision = "014_crm_campana_programado"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gmail_temporal",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("correo_origen", sa.String(255), nullable=False),
        sa.Column("asunto", sa.String(500), nullable=True),
        sa.Column("fecha_pago", sa.String(100), nullable=True),
        sa.Column("cedula", sa.String(50), nullable=True),
        sa.Column("monto", sa.String(100), nullable=True),
        sa.Column("numero_referencia", sa.String(200), nullable=True),
        sa.Column("drive_file_id", sa.String(100), nullable=True),
        sa.Column("drive_link", sa.String(500), nullable=True),
        sa.Column("drive_email_link", sa.String(500), nullable=True),
        sa.Column("sheet_name", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gmail_temporal_created_at", "gmail_temporal", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_gmail_temporal_created_at", table_name="gmail_temporal")
    op.drop_table("gmail_temporal")
