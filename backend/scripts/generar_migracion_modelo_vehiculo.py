#!/usr/bin/env python3
"""
Script para generar migración de Alembic para agregar columna modelo_vehiculo
"""

import sys
import logging

# Constantes de configuración
MODELO_VEHICULO_LENGTH = 100

# Configurar logging
logging.basicConfig
logger = logging.getLogger(__name__)

# Agregar el directorio del proyecto al path


def generar_migracion():
    """Generar migración para agregar columna modelo_vehiculo"""
    from datetime import datetime
    
    # Generar nombre de archivo con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"alembic/versions/{timestamp}_add_modelo_vehiculo_to_clientes.py"

    migracion_content = f'''"""Add modelo_vehiculo column to clientes table

Revises:

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
down_revision = None  # Cambiar por la revisión anterior
branch_labels = None
depends_on = None

MODELO_VEHICULO_LENGTH = {MODELO_VEHICULO_LENGTH}


def upgrade():
    """Agregar columna modelo_vehiculo a la tabla clientes"""
    # Verificar si la columna ya existe
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('clientes')]

    if 'modelo_vehiculo' not in columns:
        op.add_column('clientes', sa.Column('modelo_vehiculo', sa.String(MODELO_VEHICULO_LENGTH), nullable=True))
    else:
        pass  # Columna ya existe


def downgrade():
    """Eliminar columna modelo_vehiculo de la tabla clientes"""
    # Verificar si la columna existe antes de eliminarla
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('clientes')]

    if 'modelo_vehiculo' in columns:
        op.drop_column('clientes', 'modelo_vehiculo')
    else:
        pass  # Columna no existe
'''

    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(migracion_content)

        logger.info(f"Migración generada: {filename}")
        logger.info("1. Ejecutar: alembic upgrade head")
        logger.info("2. Verificar que la columna se agregó correctamente")

    except Exception as e:
        logger.error(f"Error generando migración: {e}")


if __name__ == "__main__":
    generar_migracion()

"""
"""