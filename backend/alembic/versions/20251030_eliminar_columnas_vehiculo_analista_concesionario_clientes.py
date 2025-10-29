"""eliminar columnas modelo_vehiculo concesionario analista de clientes

Revision ID: 20251030_eliminar_columnas_clientes
Revises: 20251030_columnas_prestamos
Create Date: 2025-10-30 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '20251030_eliminar_columnas_clientes'
down_revision = '20251030_columnas_prestamos'
branch_labels = None
depends_on = None


def upgrade():
    # Verificar si las columnas existen antes de eliminarlas
    connection = op.get_bind()
    inspector = inspect(connection)
    
    # Verificar que la tabla clientes existe
    if 'clientes' not in inspector.get_table_names():
        print("⚠️ Tabla 'clientes' no existe, saltando migración")
        return
    
    columns = [col['name'] for col in inspector.get_columns('clientes')]
    indexes = [idx['name'] for idx in inspector.get_indexes('clientes')]
    
    # Eliminar índice y columna modelo_vehiculo si existe
    if 'modelo_vehiculo' in columns:
        # Eliminar índice si existe
        if 'idx_clientes_modelo_vehiculo' in indexes:
            try:
                op.drop_index('idx_clientes_modelo_vehiculo', table_name='clientes')
                print("✅ Índice 'idx_clientes_modelo_vehiculo' eliminado")
            except Exception as e:
                print(f"⚠️ No se pudo eliminar el índice: {e}")
        
        op.drop_column('clientes', 'modelo_vehiculo')
        print("✅ Columna 'modelo_vehiculo' eliminada de tabla clientes")
    
    # Eliminar índice y columna concesionario si existe
    if 'concesionario' in columns:
        # Eliminar índice si existe
        if 'idx_clientes_concesionario' in indexes:
            try:
                op.drop_index('idx_clientes_concesionario', table_name='clientes')
                print("✅ Índice 'idx_clientes_concesionario' eliminado")
            except Exception as e:
                print(f"⚠️ No se pudo eliminar el índice: {e}")
        
        op.drop_column('clientes', 'concesionario')
        print("✅ Columna 'concesionario' eliminada de tabla clientes")
    
    # Eliminar índice y columna analista si existe
    if 'analista' in columns:
        # Eliminar índice si existe
        if 'idx_clientes_analista' in indexes:
            try:
                op.drop_index('idx_clientes_analista', table_name='clientes')
                print("✅ Índice 'idx_clientes_analista' eliminado")
            except Exception as e:
                print(f"⚠️ No se pudo eliminar el índice: {e}")
        
        op.drop_column('clientes', 'analista')
        print("✅ Columna 'analista' eliminada de tabla clientes")


def downgrade():
    # Restaurar las columnas si fueron eliminadas
    connection = op.get_bind()
    inspector = inspect(connection)
    
    if 'clientes' not in inspector.get_table_names():
        print("⚠️ Tabla 'clientes' no existe, saltando downgrade")
        return
    
    columns = [col['name'] for col in inspector.get_columns('clientes')]
    
    # Restaurar columna modelo_vehiculo si no existe
    if 'modelo_vehiculo' not in columns:
        op.add_column('clientes', sa.Column('modelo_vehiculo', sa.String(length=100), nullable=True))
        op.create_index('idx_clientes_modelo_vehiculo', 'clientes', ['modelo_vehiculo'])
        print("✅ Columna 'modelo_vehiculo' restaurada en tabla clientes")
    
    # Restaurar columna concesionario si no existe
    if 'concesionario' not in columns:
        op.add_column('clientes', sa.Column('concesionario', sa.String(length=100), nullable=True))
        op.create_index('idx_clientes_concesionario', 'clientes', ['concesionario'])
        print("✅ Columna 'concesionario' restaurada en tabla clientes")
    
    # Restaurar columna analista si no existe
    if 'analista' not in columns:
        op.add_column('clientes', sa.Column('analista', sa.String(length=100), nullable=True))
        op.create_index('idx_clientes_analista', 'clientes', ['analista'])
        print("✅ Columna 'analista' restaurada en tabla clientes")

