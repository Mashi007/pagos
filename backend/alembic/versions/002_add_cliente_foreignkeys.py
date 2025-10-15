"""Agregar ForeignKeys a modelo Cliente para concesionarios y modelos de vehículos

Revision ID: 002_add_cliente_foreignkeys
Revises: 001_actualizar_esquema_er
Create Date: 2025-10-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_add_cliente_foreignkeys'
down_revision = '001_actualizar_esquema_er'
branch_labels = None
depends_on = None


def upgrade():
    """Agregar ForeignKeys al modelo Cliente"""
    
    # 1. Agregar nuevas columnas con ForeignKeys
    op.add_column('clientes', sa.Column('concesionario_id', sa.Integer(), nullable=True))
    op.add_column('clientes', sa.Column('modelo_vehiculo_id', sa.Integer(), nullable=True))
    op.add_column('clientes', sa.Column('asesor_config_id', sa.Integer(), nullable=True))
    
    # 2. Crear índices para las nuevas columnas
    op.create_index('ix_clientes_concesionario_id', 'clientes', ['concesionario_id'])
    op.create_index('ix_clientes_modelo_vehiculo_id', 'clientes', ['modelo_vehiculo_id'])
    op.create_index('ix_clientes_asesor_config_id', 'clientes', ['asesor_config_id'])
    
    # 3. Crear ForeignKeys
    op.create_foreign_key(
        'fk_clientes_concesionario_id', 
        'clientes', 
        'concesionarios', 
        ['concesionario_id'], 
        ['id'],
        ondelete='SET NULL'
    )
    
    op.create_foreign_key(
        'fk_clientes_modelo_vehiculo_id', 
        'clientes', 
        'modelos_vehiculos', 
        ['modelo_vehiculo_id'], 
        ['id'],
        ondelete='SET NULL'
    )
    
    op.create_foreign_key(
        'fk_clientes_asesor_config_id', 
        'clientes', 
        'asesores', 
        ['asesor_config_id'], 
        ['id'],
        ondelete='SET NULL'
    )
    
    # 4. Migrar datos existentes (opcional - solo si hay datos)
    # Nota: En producción, se debería hacer un script separado para migrar datos
    # Por ahora, las nuevas columnas quedarán NULL hasta que se actualicen manualmente
    
    print("✅ ForeignKeys agregadas al modelo Cliente")
    print("⚠️  IMPORTANTE: Las nuevas columnas están NULL. Actualizar manualmente si es necesario.")
    print("   - concesionario_id: Mapear desde campo 'concesionario' (String)")
    print("   - modelo_vehiculo_id: Mapear desde campo 'modelo_vehiculo' (String)")
    print("   - asesor_config_id: Mapear desde tabla 'asesores' si es necesario")


def downgrade():
    """Remover ForeignKeys del modelo Cliente"""
    
    # 1. Eliminar ForeignKeys
    op.drop_constraint('fk_clientes_asesor_config_id', 'clientes', type_='foreignkey')
    op.drop_constraint('fk_clientes_modelo_vehiculo_id', 'clientes', type_='foreignkey')
    op.drop_constraint('fk_clientes_concesionario_id', 'clientes', type_='foreignkey')
    
    # 2. Eliminar índices
    op.drop_index('ix_clientes_asesor_config_id', 'clientes')
    op.drop_index('ix_clientes_modelo_vehiculo_id', 'clientes')
    op.drop_index('ix_clientes_concesionario_id', 'clientes')
    
    # 3. Eliminar columnas
    op.drop_column('clientes', 'asesor_config_id')
    op.drop_column('clientes', 'modelo_vehiculo_id')
    op.drop_column('clientes', 'concesionario_id')
    
    print("✅ ForeignKeys removidas del modelo Cliente")
