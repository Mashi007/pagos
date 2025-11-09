"""Eliminar columna referencia_pago de pagos

Revision ID: 20251029_referencia_pago
Revises: 20251028_pagos
Create Date: 2025-10-29

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251029_referencia_pago'
down_revision = '20251028_pagos'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    if 'pagos' not in inspector.get_table_names():
        print("⚠️ Tabla 'pagos' no existe, saltando migración")
        return

    columns = [col['name'] for col in inspector.get_columns('pagos')]

    # Eliminar columna referencia_pago de la tabla pagos
    if 'referencia_pago' in columns:
        op.drop_column('pagos', 'referencia_pago')
    else:
        print("⚠️ Columna 'referencia_pago' no existe en tabla 'pagos'")


def downgrade():
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    if 'pagos' not in inspector.get_table_names():
        return

    columns = [col['name'] for col in inspector.get_columns('pagos')]

    # Revertir: agregar columna referencia_pago si no existe
    if 'referencia_pago' not in columns:
        op.add_column('pagos', sa.Column('referencia_pago', sa.String(length=100), nullable=False, server_default=''))
