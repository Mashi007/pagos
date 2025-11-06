"""fix_campo_resultado_aprobaciones

Revision ID: fix_campo_resultado
Revises: update_evaluacion_7_criterios
Create Date: 2025-10-28

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fix_campo_resultado'
down_revision = 'update_evaluacion_7_criterios'
branch_labels = None
depends_on = None


def upgrade():
    # Verificar si la columna resultado no existe antes de agregarla
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('aprobaciones')]
    
    if 'resultado' not in columns:
        op.add_column('aprobaciones', sa.Column('resultado', sa.Text(), nullable=True))
        print("✅ Columna 'resultado' agregada a tabla aprobaciones")


def downgrade():
    # Eliminar la columna si existe
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('aprobaciones')]
    
    if 'resultado' in columns:
        op.drop_column('aprobaciones', 'resultado')
        print("✅ Columna 'resultado' eliminada de tabla aprobaciones")

