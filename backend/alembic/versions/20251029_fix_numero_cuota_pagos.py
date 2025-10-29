"""Hacer numero_cuota nullable en tabla pagos

Revision ID: 20251029_numero_cuota_pagos
Revises: 20251029_referencia_pago
Create Date: 2025-10-29

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251029_numero_cuota_pagos'
down_revision = '20251029_referencia_pago'
branch_labels = None
depends_on = None


def upgrade():
    # Hacer numero_cuota nullable en la tabla pagos
    # Primero verificar si la columna existe, si no existe, agregarla
    from sqlalchemy import inspect
    conn = op.get_bind()
    
    # Verificar si la columna existe
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('pagos')]
    
    if 'numero_cuota' not in columns:
        # Si no existe, agregarla como nullable
        op.add_column('pagos', sa.Column('numero_cuota', sa.Integer(), nullable=True))
    else:
        # Si existe pero es NOT NULL, hacerla nullable
        op.alter_column('pagos', 'numero_cuota',
                       existing_type=sa.Integer(),
                       nullable=True)


def downgrade():
    # Revertir: hacer numero_cuota NOT NULL con valor por defecto
    op.alter_column('pagos', 'numero_cuota',
                   existing_type=sa.Integer(),
                   nullable=False,
                   server_default=sa.text('0'))

