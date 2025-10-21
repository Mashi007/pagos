"""EMERGENCY: Force remove unique index ix_clientes_cedula

Revision ID: 016_emergency_remove_unique_index_cedula
Revises: 015_remove_unique_constraint_cedula_fixed
Create Date: 2025-01-21 02:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '016_emergency_remove_unique_index_cedula'
down_revision = '015_remove_unique_constraint_cedula_fixed'
branch_labels = None
depends_on = None


def upgrade():
    """EMERGENCY: Force remove the unique index ix_clientes_cedula"""
    # Drop the problematic unique index
    op.execute("DROP INDEX IF EXISTS ix_clientes_cedula")
    
    # Create a non-unique index for performance
    op.execute("CREATE INDEX IF NOT EXISTS idx_clientes_cedula_performance ON clientes (cedula)")


def downgrade():
    """Restore the unique index"""
    # Drop the performance index
    op.execute("DROP INDEX IF EXISTS idx_clientes_cedula_performance")
    
    # Restore the unique index
    op.execute("CREATE UNIQUE INDEX ix_clientes_cedula ON clientes (cedula)")
