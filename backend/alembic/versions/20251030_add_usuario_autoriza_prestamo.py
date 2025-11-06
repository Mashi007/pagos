"""agregar columna usuario_autoriza a prestamos

Revision ID: 20251030_usuario_autoriza
Revises: 20251030_actualizar_catalogos, 20250127_performance_indexes
Create Date: 2025-10-30 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '20251030_usuario_autoriza'
down_revision = '20251030_actualizar_catalogos'
branch_labels = None
depends_on = None


def upgrade():
    # Verificar si la columna ya existe antes de agregarla
    connection = op.get_bind()
    inspector = inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('prestamos')]
    
    # Agregar columna usuario_autoriza si no existe
    if 'usuario_autoriza' not in columns:
        op.add_column('prestamos', sa.Column('usuario_autoriza', sa.String(length=100), nullable=True))
        print("✅ Columna 'usuario_autoriza' agregada a tabla prestamos")
    else:
        print("⚠️ Columna 'usuario_autoriza' ya existe en tabla prestamos")


def downgrade():
    # Eliminar la columna si existe
    connection = op.get_bind()
    inspector = inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('prestamos')]
    
    if 'usuario_autoriza' in columns:
        op.drop_column('prestamos', 'usuario_autoriza')
        print("✅ Columna 'usuario_autoriza' eliminada de tabla prestamos")

