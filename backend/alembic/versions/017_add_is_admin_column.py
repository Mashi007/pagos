"""add_is_admin_column_to_users

Revision ID: 017_add_is_admin_column
Revises: 016_emergency_remove_unique_index_cedula
Create Date: 2025-10-25 18:55:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '017_add_is_admin_column'
down_revision = '016_emergency_rm_unique_idx'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Agregar columna is_admin a la tabla users
    op.add_column('users', sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    # Eliminar columna is_admin de la tabla users
    op.drop_column('users', 'is_admin')
