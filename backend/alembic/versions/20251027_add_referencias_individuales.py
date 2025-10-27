"""add referencias individuales

Revision ID: add_referencias_individuales
Revises: update_evaluacion_7_criterios
Create Date: 2025-10-27 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_referencias_individuales'
down_revision = 'update_evaluacion_7_criterios'
branch_labels = None
depends_on = None


def upgrade():
    # Agregar campos para 3 referencias individuales
    op.add_column('prestamos_evaluacion', sa.Column('referencia1_calificacion', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('prestamos_evaluacion', sa.Column('referencia1_observaciones', sa.String(length=200), nullable=True))
    op.add_column('prestamos_evaluacion', sa.Column('referencia2_calificacion', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('prestamos_evaluacion', sa.Column('referencia2_observaciones', sa.String(length=200), nullable=True))
    op.add_column('prestamos_evaluacion', sa.Column('referencia3_calificacion', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('prestamos_evaluacion', sa.Column('referencia3_observaciones', sa.String(length=200), nullable=True))
    

def downgrade():
    # Eliminar las nuevas columnas
    op.drop_column('prestamos_evaluacion', 'referencia3_observaciones')
    op.drop_column('prestamos_evaluacion', 'referencia3_calificacion')
    op.drop_column('prestamos_evaluacion', 'referencia2_observaciones')
    op.drop_column('prestamos_evaluacion', 'referencia2_calificacion')
    op.drop_column('prestamos_evaluacion', 'referencia1_observaciones')
    op.drop_column('prestamos_evaluacion', 'referencia1_calificacion')

