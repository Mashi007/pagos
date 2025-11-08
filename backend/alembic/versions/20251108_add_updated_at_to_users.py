"""add updated_at column to users

Revision ID: 20251108_add_updated_at
Revises: 20251108_add_last_login
Create Date: 2025-11-08 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '20251108_add_updated_at'
down_revision = '20251108_add_last_login'
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

    if "updated_at" not in columns:
        # La columna no existe, agregarla
        op.add_column("users", sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.func.now()))
        print("✅ Columna 'updated_at' agregada a la tabla 'users'")
    else:
        print("✅ Columna 'updated_at' ya existe en la tabla 'users'")


def downgrade() -> None:
    # Verificar si la columna existe antes de eliminarla
    connection = op.get_bind()
    inspector = inspect(connection)
    
    if "users" not in inspector.get_table_names():
        print("⚠️ Tabla 'users' no existe, saltando downgrade")
        return
    
    columns = [col["name"] for col in inspector.get_columns("users")]
    
    if "updated_at" in columns:
        op.drop_column("users", "updated_at")
        print("✅ Columna 'updated_at' eliminada de la tabla 'users'")
    else:
        print("⚠️ Columna 'updated_at' no existe en la tabla 'users'")

