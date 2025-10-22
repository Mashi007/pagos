"""remove unique constraint from cedula

Revision ID: 014_remove_unique_constraint_cedula
Revises: 013_create_pagos_table
Create Date: 2025-01-21 01:25:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '014_remove_unique_constraint_cedula'
down_revision = '013_create_pagos_table'
branch_labels = None
depends_on = None


def upgrade():
    """Remove unique constraint from cedula column in clientes table"""
    # Drop the unique constraint on cedula column
    op.drop_constraint('clientes_cedula_key', 'clientes', type_='unique')

    # Keep the index for performance
    # op.create_index('ix_clientes_cedula', 'clientes', ['cedula'])


def downgrade():
    """Restore unique constraint on cedula column in clientes table"""
    # Restore the unique constraint
    op.create_unique_constraint('clientes_cedula_key', 'clientes', ['cedula'])
