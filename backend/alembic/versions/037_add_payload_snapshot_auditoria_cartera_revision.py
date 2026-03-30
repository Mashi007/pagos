"""Add payload_snapshot column to auditoria_cartera_revision table

Revision ID: 037_add_payload_snapshot_auditoria
Revises: 036_add_metadata_tecnica
Create Date: 2026-03-30 09:13:30.000000

Error fixed:
  psycopg2.errors.UndefinedColumn: column "payload_snapshot" of relation "auditoria_cartera_revision" does not exist
  
The auditoria_cartera_revision model defines payload_snapshot (JSONB column) but the database schema 
doesn't have it. This migration adds the missing column.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '037_add_payload_snapshot_auditoria'
down_revision = '036_add_metadata_tecnica'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add payload_snapshot column as JSONB, nullable
    op.add_column('auditoria_cartera_revision', 
        sa.Column('payload_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )


def downgrade() -> None:
    # Remove payload_snapshot column
    op.drop_column('auditoria_cartera_revision', 'payload_snapshot')
