#!/usr/bin/env python3
"""
Script para generar migración de Alembic para agregar columna modelo_vehiculo
"""

import os
import sys
from datetime import datetime

# Agregar el directorio del proyecto al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def generar_migracion():
    """Generar migración para agregar columna modelo_vehiculo"""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"backend/alembic/versions/{timestamp}_add_modelo_vehiculo_column.py"
    
    migracion_content = f'''"""Add modelo_vehiculo column to clientes table

Revision ID: {timestamp}
Revises: 
Create Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '{timestamp}'
down_revision = None  # Cambiar por la revisión anterior
branch_labels = None
depends_on = None

def upgrade():
    """Agregar columna modelo_vehiculo a la tabla clientes"""
    # Verificar si la columna ya existe
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('clientes')]
    
    if 'modelo_vehiculo' not in columns:
        op.add_column('clientes', sa.Column('modelo_vehiculo', sa.String(100), nullable=True))
        print("✅ Columna modelo_vehiculo agregada a la tabla clientes")
    else:
        print("ℹ️ Columna modelo_vehiculo ya existe en la tabla clientes")

def downgrade():
    """Eliminar columna modelo_vehiculo de la tabla clientes"""
    # Verificar si la columna existe antes de eliminarla
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('clientes')]
    
    if 'modelo_vehiculo' in columns:
        op.drop_column('clientes', 'modelo_vehiculo')
        print("✅ Columna modelo_vehiculo eliminada de la tabla clientes")
    else:
        print("ℹ️ Columna modelo_vehiculo no existe en la tabla clientes")
'''
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(migracion_content)
        
        print(f"✅ Migración generada: {filename}")
        print("📋 Próximos pasos:")
        print("1. Ejecutar: alembic upgrade head")
        print("2. Verificar que la columna se agregó correctamente")
        
    except Exception as e:
        print(f"❌ Error generando migración: {e}")

if __name__ == "__main__":
    generar_migracion()
