"""Tabla drive_clientes_candidatos_cache (lista precomputada Clientes desde Drive).

Revision ID: 057_drive_clientes_candidatos_cache
Revises: 056_auditoria_cliente_alta_desde_drive
Create Date: 2026-04-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "057_drive_clientes_candidatos_cache"
down_revision = "056_auditoria_cliente_alta_desde_drive"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "drive_clientes_candidatos_cache" in insp.get_table_names():
        return
    op.create_table(
        "drive_clientes_candidatos_cache",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("drive_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "drive_clientes_candidatos_cache" not in insp.get_table_names():
        return
    op.drop_table("drive_clientes_candidatos_cache")
