"""Add metadata_tecnica column to envios_notificacion table

Revision ID: 036_add_metadata_tecnica
Revises: 035_fix_materialized_views_indices
Create Date: 2026-03-30 09:04:00.000000

Error fixed:
  psycopg2.errors.UndefinedColumn: column "metadata_tecnica" of relation "envios_notificacion" does not exist
  
The envios_notificacion model defines metadata_tecnica (JSON column) but the database schema 
doesn't have it. This migration adds the missing column.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '036_add_metadata_tecnica'
down_revision = '035_fix_mv_indices'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    cols = {c["name"] for c in insp.get_columns("envios_notificacion")}
    if "metadata_tecnica" in cols:
        return
    op.add_column(
        "envios_notificacion",
        sa.Column("metadata_tecnica", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    cols = {c["name"] for c in insp.get_columns("envios_notificacion")}
    if "metadata_tecnica" not in cols:
        return
    op.drop_column("envios_notificacion", "metadata_tecnica")
