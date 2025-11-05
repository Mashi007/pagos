"""add valor_activo to prestamos

Revision ID: 20250115_valor_activo
Revises: 20251104_group_by_indexes
Create Date: 2025-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '20250115_valor_activo'
down_revision = '20251104_group_by_indexes'
branch_labels = None
depends_on = None


def upgrade():
    # Verificar si la columna ya existe antes de agregarla
    connection = op.get_bind()
    inspector = inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('prestamos')]
    
    # Agregar columna valor_activo si no existe
    if 'valor_activo' not in columns:
        op.add_column('prestamos', sa.Column('valor_activo', sa.Numeric(precision=15, scale=2), nullable=True))
        print("✅ Columna 'valor_activo' agregada a tabla prestamos")
    else:
        print("⚠️ Columna 'valor_activo' ya existe en tabla prestamos")


def downgrade():
    # Eliminar la columna si existe
    connection = op.get_bind()
    inspector = inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('prestamos')]
    
    if 'valor_activo' in columns:
        op.drop_column('prestamos', 'valor_activo')
        print("✅ Columna 'valor_activo' eliminada de tabla prestamos")
    else:
        print("⚠️ Columna 'valor_activo' no existe en tabla prestamos")

