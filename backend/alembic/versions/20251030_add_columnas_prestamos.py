"""agregar columnas concesionario analista modelo_vehiculo a prestamos

Revision ID: 20251030_columnas_prestamos
Revises: 20251029_numero_cuota_pagos
Create Date: 2025-10-30 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '20251030_columnas_prestamos'
down_revision = '20251029_numero_cuota_pagos'
branch_labels = None
depends_on = None


def upgrade():
    # Verificar si las columnas ya existen antes de agregarlas
    connection = op.get_bind()
    inspector = inspect(connection)

    if 'prestamos' not in inspector.get_table_names():
        print("⚠️ Tabla 'prestamos' no existe, saltando migración")
        return

    columns = [col['name'] for col in inspector.get_columns('prestamos')]

    # Agregar columna concesionario si no existe
    if 'concesionario' not in columns:
        op.add_column('prestamos', sa.Column('concesionario', sa.String(length=100), nullable=True))
        print("✅ Columna 'concesionario' agregada a tabla prestamos")

    # Agregar columna analista si no existe
    if 'analista' not in columns:
        op.add_column('prestamos', sa.Column('analista', sa.String(length=100), nullable=True))
        print("✅ Columna 'analista' agregada a tabla prestamos")

    # Agregar columna modelo_vehiculo si no existe
    if 'modelo_vehiculo' not in columns:
        op.add_column('prestamos', sa.Column('modelo_vehiculo', sa.String(length=100), nullable=True))
        print("✅ Columna 'modelo_vehiculo' agregada a tabla prestamos")


def downgrade():
    # Eliminar las columnas si existen
    connection = op.get_bind()
    inspector = inspect(connection)

    if 'prestamos' not in inspector.get_table_names():
        return

    columns = [col['name'] for col in inspector.get_columns('prestamos')]

    if 'modelo_vehiculo' in columns:
        op.drop_column('prestamos', 'modelo_vehiculo')
        print("✅ Columna 'modelo_vehiculo' eliminada de tabla prestamos")

    if 'analista' in columns:
        op.drop_column('prestamos', 'analista')
        print("✅ Columna 'analista' eliminada de tabla prestamos")

    if 'concesionario' in columns:
        op.drop_column('prestamos', 'concesionario')
        print("✅ Columna 'concesionario' eliminada de tabla prestamos")
