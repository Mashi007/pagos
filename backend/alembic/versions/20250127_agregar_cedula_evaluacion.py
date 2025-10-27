"""agregar cedula a evaluacion

Revision ID: agregar_cedula
Revises: add_referencias_individuales
Create Date: 2025-01-27

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'agregar_cedula'
down_revision = 'add_referencias_individuales'
branch_labels = None
depends_on = None


def upgrade():
    # Agregar columna cedula a la tabla prestamos_evaluacion
    op.add_column('prestamos_evaluacion', sa.Column('cedula', sa.String(length=20), nullable=True))
    
    # Crear índice para búsquedas rápidas por cédula
    op.create_index('ix_prestamos_evaluacion_cedula', 'prestamos_evaluacion', ['cedula'], unique=False)
    
    # Actualizar registros existentes con la cédula desde la tabla prestamos
    op.execute("""
        UPDATE prestamos_evaluacion e
        SET cedula = p.cedula
        FROM prestamos p
        WHERE e.prestamo_id = p.id;
    """)
    
    # Hacer la columna NOT NULL después de poblarla
    op.alter_column('prestamos_evaluacion', 'cedula', nullable=False)


def downgrade():
    # Eliminar índice
    op.drop_index('ix_prestamos_evaluacion_cedula', table_name='prestamos_evaluacion')
    
    # Eliminar columna
    op.drop_column('prestamos_evaluacion', 'cedula')

