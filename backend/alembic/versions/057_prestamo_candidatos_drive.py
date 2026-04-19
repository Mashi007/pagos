"""Tabla prestamo_candidatos_drive (snapshot candidatos préstamo desde hoja CONCILIACIÓN).

Revision ID: 057_prestamo_candidatos_drive
Revises: 056_auditoria_cliente_alta_desde_drive
Create Date: 2026-04-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "057_prestamo_candidatos_drive"
down_revision = "056_auditoria_cliente_alta_desde_drive"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "prestamo_candidatos_drive" in insp.get_table_names():
        return
    op.create_table(
        "prestamo_candidatos_drive",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("sheet_row_number", sa.Integer(), nullable=False),
        sa.Column("cedula_cmp", sa.String(length=32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_prestamo_candidatos_drive_sheet_row_number",
        "prestamo_candidatos_drive",
        ["sheet_row_number"],
        unique=False,
    )
    op.create_index(
        "ix_prestamo_candidatos_drive_cedula_cmp",
        "prestamo_candidatos_drive",
        ["cedula_cmp"],
        unique=False,
    )
    op.create_index(
        "ix_prestamo_candidatos_drive_computed_at",
        "prestamo_candidatos_drive",
        ["computed_at"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "prestamo_candidatos_drive" not in insp.get_table_names():
        return
    op.drop_index("ix_prestamo_candidatos_drive_computed_at", table_name="prestamo_candidatos_drive")
    op.drop_index("ix_prestamo_candidatos_drive_cedula_cmp", table_name="prestamo_candidatos_drive")
    op.drop_index("ix_prestamo_candidatos_drive_sheet_row_number", table_name="prestamo_candidatos_drive")
    op.drop_table("prestamo_candidatos_drive")
