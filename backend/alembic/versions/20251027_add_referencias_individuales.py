"""add referencias individuales

Revision ID: add_referencias_individuales
Revises: update_evaluacion_7_criterios
Create Date: 2025-10-27 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_referencias_individuales'
down_revision = 'update_evaluacion_7_criterios'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    inspector = inspect(connection)

    if 'prestamos_evaluacion' not in inspector.get_table_names():
        print("⚠️ Tabla 'prestamos_evaluacion' no existe, saltando migración")
        return

    columns = [col['name'] for col in inspector.get_columns('prestamos_evaluacion')]

    # Agregar campos para 3 referencias individuales
    if 'referencia1_calificacion' not in columns:
        op.add_column('prestamos_evaluacion', sa.Column('referencia1_calificacion', sa.Integer(), nullable=True, server_default='0'))
    if 'referencia1_observaciones' not in columns:
        op.add_column('prestamos_evaluacion', sa.Column('referencia1_observaciones', sa.String(length=200), nullable=True))
    if 'referencia2_calificacion' not in columns:
        op.add_column('prestamos_evaluacion', sa.Column('referencia2_calificacion', sa.Integer(), nullable=True, server_default='0'))
    if 'referencia2_observaciones' not in columns:
        op.add_column('prestamos_evaluacion', sa.Column('referencia2_observaciones', sa.String(length=200), nullable=True))
    if 'referencia3_calificacion' not in columns:
        op.add_column('prestamos_evaluacion', sa.Column('referencia3_calificacion', sa.Integer(), nullable=True, server_default='0'))
    if 'referencia3_observaciones' not in columns:
        op.add_column('prestamos_evaluacion', sa.Column('referencia3_observaciones', sa.String(length=200), nullable=True))


def downgrade():
    connection = op.get_bind()
    inspector = inspect(connection)

    if 'prestamos_evaluacion' not in inspector.get_table_names():
        return

    columns = [col['name'] for col in inspector.get_columns('prestamos_evaluacion')]

    # Eliminar las nuevas columnas si existen
    if 'referencia3_observaciones' in columns:
        op.drop_column('prestamos_evaluacion', 'referencia3_observaciones')
    if 'referencia3_calificacion' in columns:
        op.drop_column('prestamos_evaluacion', 'referencia3_calificacion')
    if 'referencia2_observaciones' in columns:
        op.drop_column('prestamos_evaluacion', 'referencia2_observaciones')
    if 'referencia2_calificacion' in columns:
        op.drop_column('prestamos_evaluacion', 'referencia2_calificacion')
    if 'referencia1_observaciones' in columns:
        op.drop_column('prestamos_evaluacion', 'referencia1_observaciones')
    if 'referencia1_calificacion' in columns:
        op.drop_column('prestamos_evaluacion', 'referencia1_calificacion')
