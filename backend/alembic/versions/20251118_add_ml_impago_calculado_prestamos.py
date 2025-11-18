"""agregar campos ml_impago_calculado a prestamos

Revision ID: 20251118_ml_impago_calculado
Revises: 20251114_05_modelos_impago_cuotas
Create Date: 2025-11-18

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '20251118_ml_impago_calculado'
down_revision = '20251114_05_modelos_impago_cuotas'
branch_labels = None
depends_on = None


def upgrade():
    """
    Agregar campos para guardar predicciones ML Impago calculadas en tabla prestamos.
    Esto permite que las predicciones persistan entre reinicios del servidor.
    """
    connection = op.get_bind()
    inspector = inspect(connection)

    if 'prestamos' not in inspector.get_table_names():
        print("⚠️ Tabla 'prestamos' no existe, saltando migración")
        return

    columns = [col['name'] for col in inspector.get_columns('prestamos')]

    # Agregar columna ml_impago_nivel_riesgo_calculado si no existe
    if 'ml_impago_nivel_riesgo_calculado' not in columns:
        op.add_column('prestamos', sa.Column('ml_impago_nivel_riesgo_calculado', sa.String(length=20), nullable=True))
        print("✅ Columna 'ml_impago_nivel_riesgo_calculado' agregada a tabla prestamos")

    # Agregar columna ml_impago_probabilidad_calculada si no existe
    if 'ml_impago_probabilidad_calculada' not in columns:
        op.add_column('prestamos', sa.Column('ml_impago_probabilidad_calculada', sa.Numeric(5, 3), nullable=True))
        print("✅ Columna 'ml_impago_probabilidad_calculada' agregada a tabla prestamos")

    # Agregar columna ml_impago_calculado_en si no existe
    if 'ml_impago_calculado_en' not in columns:
        op.add_column('prestamos', sa.Column('ml_impago_calculado_en', sa.TIMESTAMP(), nullable=True))
        print("✅ Columna 'ml_impago_calculado_en' agregada a tabla prestamos")

    # Agregar columna ml_impago_modelo_id si no existe (FK a modelos_impago_cuotas)
    if 'ml_impago_modelo_id' not in columns:
        op.add_column('prestamos', sa.Column('ml_impago_modelo_id', sa.Integer(), nullable=True))
        # Agregar foreign key si la tabla modelos_impago_cuotas existe
        if 'modelos_impago_cuotas' in inspector.get_table_names():
            op.create_foreign_key(
                'fk_prestamos_ml_impago_modelo',
                'prestamos',
                'modelos_impago_cuotas',
                ['ml_impago_modelo_id'],
                ['id']
            )
        print("✅ Columna 'ml_impago_modelo_id' agregada a tabla prestamos")

    # Crear índice para mejorar consultas
    try:
        op.create_index('ix_prestamos_ml_impago_calculado_en', 'prestamos', ['ml_impago_calculado_en'])
        print("✅ Índice 'ix_prestamos_ml_impago_calculado_en' creado")
    except Exception as e:
        print(f"⚠️ No se pudo crear índice (puede que ya exista): {e}")


def downgrade():
    """Eliminar campos de predicciones ML calculadas"""
    connection = op.get_bind()
    inspector = inspect(connection)

    if 'prestamos' not in inspector.get_table_names():
        return

    columns = [col['name'] for col in inspector.get_columns('prestamos')]

    # Eliminar índice
    try:
        op.drop_index('ix_prestamos_ml_impago_calculado_en', table_name='prestamos')
        print("✅ Índice 'ix_prestamos_ml_impago_calculado_en' eliminado")
    except Exception:
        pass

    # Eliminar foreign key constraint
    try:
        op.drop_constraint('fk_prestamos_ml_impago_modelo', 'prestamos', type_='foreignkey')
        print("✅ Foreign key 'fk_prestamos_ml_impago_modelo' eliminado")
    except Exception:
        pass

    # Eliminar columnas
    if 'ml_impago_modelo_id' in columns:
        op.drop_column('prestamos', 'ml_impago_modelo_id')
        print("✅ Columna 'ml_impago_modelo_id' eliminada de tabla prestamos")

    if 'ml_impago_calculado_en' in columns:
        op.drop_column('prestamos', 'ml_impago_calculado_en')
        print("✅ Columna 'ml_impago_calculado_en' eliminada de tabla prestamos")

    if 'ml_impago_probabilidad_calculada' in columns:
        op.drop_column('prestamos', 'ml_impago_probabilidad_calculada')
        print("✅ Columna 'ml_impago_probabilidad_calculada' eliminada de tabla prestamos")

    if 'ml_impago_nivel_riesgo_calculado' in columns:
        op.drop_column('prestamos', 'ml_impago_nivel_riesgo_calculado')
        print("✅ Columna 'ml_impago_nivel_riesgo_calculado' eliminada de tabla prestamos")

