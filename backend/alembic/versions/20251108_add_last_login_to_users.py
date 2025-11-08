"""add last_login column to users

Revision ID: 20251108_add_last_login
Revises: 20251104_critical_indexes
Create Date: 2025-11-08 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '20251108_add_last_login'
down_revision = '20251104_critical_indexes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Verificar si la columna ya existe antes de agregarla
    connection = op.get_bind()
    inspector = inspect(connection)
    
    if "users" not in inspector.get_table_names():
        print("⚠️ Tabla 'users' no existe, saltando migración")
        return
    
    columns = [col["name"] for col in inspector.get_columns("users")]

    if "last_login" not in columns:
        # La columna no existe, agregarla
        op.add_column("users", sa.Column("last_login", sa.DateTime(), nullable=True))
        print("✅ Columna 'last_login' agregada a la tabla 'users'")
    else:
        print("✅ Columna 'last_login' ya existe en la tabla 'users'")


def downgrade() -> None:
    # Verificar si la columna existe antes de eliminarla
    connection = op.get_bind()
    inspector = inspect(connection)
    
    if "users" not in inspector.get_table_names():
        print("⚠️ Tabla 'users' no existe, saltando downgrade")
        return
    
    columns = [col["name"] for col in inspector.get_columns("users")]
    
    if "last_login" in columns:
        op.drop_column("users", "last_login")
        print("✅ Columna 'last_login' eliminada de la tabla 'users'")
    else:
        print("⚠️ Columna 'last_login' no existe en la tabla 'users'")

