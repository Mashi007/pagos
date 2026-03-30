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


# revision identifiers, used by Alembic.
revision = '036_add_metadata_tecnica'
down_revision = '035_fix_materialized_views_indices'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add metadata_tecnica column as JSON, nullable
    op.add_column('envios_notificacion', 
        sa.Column('metadata_tecnica', sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    # Remove metadata_tecnica column
    op.drop_column('envios_notificacion', 'metadata_tecnica')
