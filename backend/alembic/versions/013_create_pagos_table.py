"""Crear tabla pagos

Revision ID: 013_create_pagos_table
Revises: 012_add_concesionario_analista_clientes
Create Date: 2025-10-19 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '013_create_pagos_table'
down_revision = '012_add_concesionario_analista_clientes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Crear tabla pagos con todos los campos necesarios"""
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Verificar si la tabla ya existe
    if 'pagos' in inspector.get_table_names():
        print("ℹ️ Tabla 'pagos' ya existe")
        return
    
    # Crear tabla pagos
    op.create_table('pagos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cedula_cliente', sa.String(length=20), nullable=False),
        sa.Column('fecha_pago', sa.DateTime(), nullable=False),
        sa.Column('monto_pagado', sa.Float(), nullable=False),
        sa.Column('numero_documento', sa.String(length=100), nullable=False),
        sa.Column('documento_nombre', sa.String(length=255), nullable=True),
        sa.Column('documento_tipo', sa.String(length=10), nullable=True),
        sa.Column('documento_tamaño', sa.Integer(), nullable=True),
        sa.Column('documento_ruta', sa.String(length=500), nullable=True),
        sa.Column('conciliado', sa.Boolean(), nullable=False, default=False),
        sa.Column('fecha_conciliacion', sa.DateTime(), nullable=True),
        sa.Column('activo', sa.Boolean(), nullable=False, default=True),
        sa.Column('notas', sa.Text(), nullable=True),
        sa.Column('fecha_registro', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('fecha_actualizacion', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Crear índices
    op.create_index('idx_pagos_cedula_cliente', 'pagos', ['cedula_cliente'])
    op.create_index('idx_pagos_numero_documento', 'pagos', ['numero_documento'])
    op.create_index('idx_pagos_fecha_pago', 'pagos', ['fecha_pago'])
    op.create_index('idx_pagos_conciliado', 'pagos', ['conciliado'])
    op.create_index('idx_pagos_activo', 'pagos', ['activo'])
    
    print("✅ Tabla 'pagos' creada exitosamente")
    print("✅ Índices creados para optimización de consultas")


def downgrade() -> None:
    """Eliminar tabla pagos"""
    op.drop_table('pagos')
    print("✅ Tabla 'pagos' eliminada")
