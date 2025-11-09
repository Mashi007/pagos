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
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    # Verificar si la columna ya existe
    if 'users' in inspector.get_table_names():
        columns = [col["name"] for col in inspector.get_columns("users")]
        if 'is_admin' not in columns:
            op.add_column('users', sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false'))
        else:
            print("Columna 'is_admin' ya existe en la tabla 'users'")


def downgrade() -> None:
    # Eliminar columna is_admin de la tabla users
    op.drop_column('users', 'is_admin')
