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
    inspector = sa.inspect(connection)
    
    if "users" not in inspector.get_table_names():
        print("⚠️ Tabla 'users' no existe, saltando migración")
        return
    
    columns = [col["name"] for col in inspector.get_columns("users")]

    if "cargo" not in columns:
        # La columna no existe, agregarla
        op.add_column("users", sa.Column("cargo", sa.String(100), nullable=True))
        print("✅ Columna 'cargo' agregada a la tabla 'users'")
    else:
        print("Columna 'cargo' ya existe en la tabla 'users'")


def downgrade():
    # Verificar si la columna existe antes de eliminarla
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    if "users" not in inspector.get_table_names():
        return
    
    columns = [col["name"] for col in inspector.get_columns("users")]

    if "cargo" in columns:
        # La columna existe, eliminarla
        op.drop_column("users", "cargo")
        print("✅ Columna 'cargo' eliminada de la tabla 'users'")
    else:
        print("Columna 'cargo' no existe en la tabla 'users'")