"""Actualizar modelos de pagos

Revision ID: 20251028_pagos
Revises: 
Create Date: 2025-10-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251028_pagos'
down_revision = 'fix_campo_resultado'
branch_labels = None
depends_on = None


def upgrade():
    # Actualizar tabla pagos
    op.add_column('pagos', sa.Column('prestamo_id', sa.Integer(), nullable=True))
    op.add_column('pagos', sa.Column('fecha_registro', sa.DateTime(), nullable=True))
    op.add_column('pagos', sa.Column('institucion_bancaria', sa.String(length=100), nullable=True))
    op.add_column('pagos', sa.Column('referencia_pago', sa.String(length=100), nullable=False, server_default=''))
    op.add_column('pagos', sa.Column('estado', sa.String(length=20), nullable=False, server_default='PAGADO'))
    op.add_column('pagos', sa.Column('usuario_registro', sa.String(length=100), nullable=True))
    
    # Crear índice para prestamo_id
    op.create_index(op.f('ix_pagos_prestamo_id'), 'pagos', ['prestamo_id'], unique=False)
    
    # Actualizar tabla cuotas
    op.alter_column('cuotas', 'estado',
                    existing_type=sa.String(length=20),
                    comment='PENDIENTE, PAGADO, ATRASADO, PARCIAL, ADELANTADO')
    
    # Crear tabla pagos_auditoria
    op.create_table(
        'pagos_auditoria',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pago_id', sa.Integer(), nullable=False),
        sa.Column('usuario', sa.String(length=100), nullable=False),
        sa.Column('campo_modificado', sa.String(length=100), nullable=False),
        sa.Column('valor_anterior', sa.String(length=500), nullable=True),
        sa.Column('valor_nuevo', sa.String(length=500), nullable=False),
        sa.Column('accion', sa.String(length=50), nullable=False),
        sa.Column('observaciones', sa.Text(), nullable=True),
        sa.Column('fecha_cambio', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pagos_auditoria_pago_id'), 'pagos_auditoria', ['pago_id'], unique=False)
    op.create_index(op.f('ix_pagos_auditoria_fecha_cambio'), 'pagos_auditoria', ['fecha_cambio'], unique=False)


def downgrade():
    # Eliminar tabla pagos_auditoria
    op.drop_index(op.f('ix_pagos_auditoria_fecha_cambio'), table_name='pagos_auditoria')
    op.drop_index(op.f('ix_pagos_auditoria_pago_id'), table_name='pagos_auditoria')
    op.drop_table('pagos_auditoria')
    
    # Revertir cambios en cuotas
    op.alter_column('cuotas', 'estado',
                    existing_type=sa.String(length=20),
                    comment=None)
    
    # Eliminar índices y columnas de pagos
    op.drop_index(op.f('ix_pagos_prestamo_id'), table_name='pagos')
    op.drop_column('pagos', 'usuario_registro')
    op.drop_column('pagos', 'estado')
    op.drop_column('pagos', 'referencia_pago')
    op.drop_column('pagos', 'institucion_bancaria')
    op.drop_column('pagos', 'fecha_registro')
    op.drop_column('pagos', 'prestamo_id')

