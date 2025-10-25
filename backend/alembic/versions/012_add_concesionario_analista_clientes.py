
Revision ID: 012_add_concesionario_analista_clientes
Revises: 011_fix_admin_users_final
Create Date: 2025-10-19 13:30:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "012_add_concesionario_analista_clientes"
down_revision = "011_fix_admin_users_final"
branch_labels = None
depends_on = None


def upgrade():

    # Verificar si las columnas ya existen
    inspector = inspect(op.get_bind())
    columns = [col["name"] for col in inspector.get_columns("clientes")]

    # Agregar concesionario si no existe
    if "concesionario" not in columns:
        op.add_column
            "clientes", sa.Column("concesionario", sa.String(100), nullable=True)
        op.create_index("idx_clientes_concesionario", "clientes", ["concesionario"])
        print("Columna 'concesionario' agregada a la tabla 'clientes'")
    else:
        print("Columna 'concesionario' ya existe en la tabla 'clientes'")

    # Agregar analista si no existe
    if "analista" not in columns:
        op.add_column("clientes", sa.Column("analista", sa.String(100), nullable=True))
        op.create_index("idx_clientes_analista", "clientes", ["analista"])
        print("Columna 'analista' agregada a la tabla 'clientes'")
    else:
        print("Columna 'analista' ya existe en la tabla 'clientes'")


def downgrade():

    # Verificar si las columnas existen antes de eliminarlas
    inspector = inspect(op.get_bind())
    columns = [col["name"] for col in inspector.get_columns("clientes")]

    # Eliminar analista si existe
    if "analista" in columns:
        op.drop_index("idx_clientes_analista", "clientes")
        op.drop_column("clientes", "analista")
        print("Columna 'analista' eliminada de la tabla 'clientes'")

    # Eliminar concesionario si existe
    if "concesionario" in columns:
        op.drop_index("idx_clientes_concesionario", "clientes")
        op.drop_column("clientes", "concesionario")
        print("Columna 'concesionario' eliminada de la tabla 'clientes'")

"""