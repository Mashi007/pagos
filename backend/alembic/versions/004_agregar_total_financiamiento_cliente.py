"""agregar_total_financiamiento_cliente

Revision ID: 004_agregar_total_financiamiento_cliente
Revises: 003_verificar_foreign_keys
Create Date: 2025-10-13 16:40:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "004_agregar_total_financiamiento_cliente"
down_revision = "003_verificar_foreign_keys"
branch_labels = None
depends_on = None


def upgrade():
    # Verificar si la columna ya existe
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col["name"] for col in inspector.get_columns("clientes")]

    if "total_financiamiento" not in columns:
        # Agregar la columna total_financiamiento
        op.add_column
            sa.Column("total_financiamiento", sa.Numeric(12, 2), nullable=True),
        print("Columna 'total_financiamiento' agregada a la tabla 'clientes'")
    else:
        print("Columna 'total_financiamiento' ya existe en la tabla 'clientes'")


def downgrade():
    # Eliminar la columna total_financiamiento
    op.drop_column("clientes", "total_financiamiento")
