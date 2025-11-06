"""add cargo column to users

Revision ID: 007_add_cargo_column_users
Revises: 005
Create Date: 2025-10-17 20:20:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "007_add_cargo_column_users"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade():
    # Verificar si la columna ya existe antes de agregarla
    connection = op.get_bind()

    # Verificar si la columna cargo existe
    result = connection.execute(
        sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='cargo'")
    )

    if not result.fetchone():
        # La columna no existe, agregarla
        op.add_column("users", sa.Column("cargo", sa.String(100), nullable=True))
    else:
        print("Columna 'cargo' ya existe en la tabla 'users'")


def downgrade():
    # Verificar si la columna existe antes de eliminarla
    connection = op.get_bind()

    result = connection.execute(
        sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='cargo'")
    )

    if result.fetchone():
        # La columna existe, eliminarla
        op.drop_column("users", "cargo")
    else:
        print("Columna 'cargo' no existe en la tabla 'users'")