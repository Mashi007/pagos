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
    # Eliminar columna referencia_pago de la tabla pagos
    op.drop_column('pagos', 'referencia_pago')


def downgrade():
    # Revertir: agregar columna referencia_pago
    op.add_column('pagos', sa.Column('referencia_pago', sa.String(length=100), nullable=False, server_default=''))

