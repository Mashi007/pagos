"""Merge heads + tabla clientes_drive_export_excel_auditoria.

Revision ID: 058_clientes_drive_export_excel_auditoria
Revises: 057_drive_clientes_candidatos_cache, 057_gmail_drive_links_text, 057_prestamo_candidatos_drive
Create Date: 2026-04-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "058_clientes_drive_export_excel_auditoria"
down_revision = (
    "057_drive_clientes_candidatos_cache",
    "057_gmail_drive_links_text",
    "057_prestamo_candidatos_drive",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "clientes_drive_export_excel_auditoria" in insp.get_table_names():
        return
    op.create_table(
        "clientes_drive_export_excel_auditoria",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("exportado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("usuario_email", sa.String(length=255), nullable=False),
        sa.Column("modo", sa.String(length=40), nullable=False),
        sa.Column("filas_count", sa.Integer(), nullable=False),
        sa.Column("sheet_rows_json", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_clientes_drive_export_excel_auditoria_exportado_en",
        "clientes_drive_export_excel_auditoria",
        ["exportado_en"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_clientes_drive_export_excel_auditoria_exportado_en", table_name="clientes_drive_export_excel_auditoria")
    op.drop_table("clientes_drive_export_excel_auditoria")
