"""update evaluacion 7 criterios

Revision ID: update_evaluacion_7_criterios
Revises: create_tablas_prestamos
Create Date: 2025-10-27 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'update_evaluacion_7_criterios'
down_revision = 'create_tablas_prestamos'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    inspector = inspect(connection)

    if 'prestamos_evaluacion' not in inspector.get_table_names():
        print("⚠️ Tabla 'prestamos_evaluacion' no existe, saltando migración")
        return

    columns = [col['name'] for col in inspector.get_columns('prestamos_evaluacion')]

    # Agregar nuevas columnas para los 7 criterios (100 puntos)

    # ============================================
    # CRITERIO 1: CAPACIDAD DE PAGO (mantener ratio_endeudamiento y ratio_cobertura, ajustar valores)
    # ============================================
    # Columnas ya existen, solo actualizar descripción en comentarios

    # ============================================
    # CRITERIO 2: ESTABILIDAD LABORAL (23 puntos)
    # ============================================
    # Renombrar y agregar nuevas columnas
    if 'antiguedad_trabajo_puntos' not in columns:
        op.add_column('prestamos_evaluacion', sa.Column('antiguedad_trabajo_puntos', sa.Numeric(5, 2), nullable=True, server_default='0'))
    if 'meses_trabajo' not in columns:
        op.add_column('prestamos_evaluacion', sa.Column('meses_trabajo', sa.Numeric(6, 2), nullable=True))

    # Mantener tipo_empleo_puntos existente, agregar nuevos campos
    if 'tipo_empleo_descripcion' not in columns:
        op.add_column('prestamos_evaluacion', sa.Column('tipo_empleo_descripcion', sa.String(length=50), nullable=True))
    if 'sector_economico_puntos' not in columns:
        op.add_column('prestamos_evaluacion', sa.Column('sector_economico_puntos', sa.Numeric(5, 2), nullable=True, server_default='0'))
    if 'sector_economico_descripcion' not in columns:
        op.add_column('prestamos_evaluacion', sa.Column('sector_economico_descripcion', sa.String(length=50), nullable=True))

    # ============================================
    # CRITERIO 3: REFERENCIAS PERSONALES (5 puntos)
    # ============================================
    if 'referencias_puntos' not in columns:
        op.add_column('prestamos_evaluacion', sa.Column('referencias_puntos', sa.Numeric(5, 2), nullable=True, server_default='0'))
    if 'referencias_descripcion' not in columns:
        op.add_column('prestamos_evaluacion', sa.Column('referencias_descripcion', sa.String(length=50), nullable=True))
    if 'num_referencias_verificadas' not in columns:
        op.add_column('prestamos_evaluacion', sa.Column('num_referencias_verificadas', sa.Integer(), nullable=True))

    # ============================================
    # CRITERIO 4: ARRAIGO GEOGRÁFICO (12 puntos)
    # ============================================
    if 'arraigo_vivienda_puntos' not in columns:
        op.add_column('prestamos_evaluacion', sa.Column('arraigo_vivienda_puntos', sa.Numeric(5, 2), nullable=True, server_default='0'))
    if 'arraigo_familiar_puntos' not in columns:
        op.add_column('prestamos_evaluacion', sa.Column('arraigo_familiar_puntos', sa.Numeric(5, 2), nullable=True, server_default='0'))
    if 'arraigo_laboral_puntos' not in columns:
        op.add_column('prestamos_evaluacion', sa.Column('arraigo_laboral_puntos', sa.Numeric(5, 2), nullable=True, server_default='0'))

    # ============================================
    # CRITERIO 5: PERFIL SOCIODEMOGRÁFICO (17 puntos)
    # ============================================
    if 'vivienda_puntos' not in columns:
        op.add_column('prestamos_evaluacion', sa.Column('vivienda_puntos', sa.Numeric(5, 2), nullable=True, server_default='0'))
    if 'vivienda_descripcion' not in columns:
        op.add_column('prestamos_evaluacion', sa.Column('vivienda_descripcion', sa.String(length=50), nullable=True))
    if 'estado_civil_puntos' not in columns:
        op.add_column('prestamos_evaluacion', sa.Column('estado_civil_puntos', sa.Numeric(5, 2), nullable=True, server_default='0'))
    if 'estado_civil_descripcion' not in columns:
        op.add_column('prestamos_evaluacion', sa.Column('estado_civil_descripcion', sa.String(length=50), nullable=True))
    if 'hijos_puntos' not in columns:
        op.add_column('prestamos_evaluacion', sa.Column('hijos_puntos', sa.Numeric(5, 2), nullable=True, server_default='0'))
    if 'hijos_descripcion' not in columns:
        op.add_column('prestamos_evaluacion', sa.Column('hijos_descripcion', sa.String(length=50), nullable=True))

    # ============================================
    # CRITERIO 6: EDAD DEL CLIENTE (5 puntos)
    # ============================================
    if 'edad_puntos' not in columns:
        op.add_column('prestamos_evaluacion', sa.Column('edad_puntos', sa.Numeric(5, 2), nullable=True, server_default='0'))
    if 'edad_cliente' not in columns:
        op.add_column('prestamos_evaluacion', sa.Column('edad_cliente', sa.Integer(), nullable=True))

    # ============================================
    # ACTUALIZAR CAMPO: requisitos_adicionales (expandir de 200 a 500 caracteres)
    # ============================================
    if 'requisitos_adicionales' in columns:
        try:
            op.alter_column('prestamos_evaluacion', 'requisitos_adicionales',
                           type_=sa.String(length=500),
                           existing_type=sa.String(length=200),
                           existing_nullable=True)
        except Exception as e:
            print(f"⚠️ No se pudo modificar columna 'requisitos_adicionales': {e}")

    # ============================================
    # ELIMINAR COLUMNAS OBSOLETAS (opcional - mantener por compatibilidad)
    # ============================================
    # NO eliminamos las columnas antiguas para mantener compatibilidad
    # Los campos antiguos serán migrados gradualmente


def downgrade():
    connection = op.get_bind()
    inspector = inspect(connection)

    if 'prestamos_evaluacion' not in inspector.get_table_names():
        return

    columns = [col['name'] for col in inspector.get_columns('prestamos_evaluacion')]

    # Eliminar las nuevas columnas agregadas si existen
    if 'edad_cliente' in columns:
        op.drop_column('prestamos_evaluacion', 'edad_cliente')
    if 'edad_puntos' in columns:
        op.drop_column('prestamos_evaluacion', 'edad_puntos')
    if 'hijos_descripcion' in columns:
        op.drop_column('prestamos_evaluacion', 'hijos_descripcion')
    if 'hijos_puntos' in columns:
        op.drop_column('prestamos_evaluacion', 'hijos_puntos')
    if 'estado_civil_descripcion' in columns:
        op.drop_column('prestamos_evaluacion', 'estado_civil_descripcion')
    if 'estado_civil_puntos' in columns:
        op.drop_column('prestamos_evaluacion', 'estado_civil_puntos')
    if 'vivienda_descripcion' in columns:
        op.drop_column('prestamos_evaluacion', 'vivienda_descripcion')
    if 'vivienda_puntos' in columns:
        op.drop_column('prestamos_evaluacion', 'vivienda_puntos')
    if 'arraigo_laboral_puntos' in columns:
        op.drop_column('prestamos_evaluacion', 'arraigo_laboral_puntos')
    if 'arraigo_familiar_puntos' in columns:
        op.drop_column('prestamos_evaluacion', 'arraigo_familiar_puntos')
    if 'arraigo_vivienda_puntos' in columns:
        op.drop_column('prestamos_evaluacion', 'arraigo_vivienda_puntos')
    if 'num_referencias_verificadas' in columns:
        op.drop_column('prestamos_evaluacion', 'num_referencias_verificadas')
    if 'referencias_descripcion' in columns:
        op.drop_column('prestamos_evaluacion', 'referencias_descripcion')
    if 'referencias_puntos' in columns:
        op.drop_column('prestamos_evaluacion', 'referencias_puntos')
    if 'sector_economico_descripcion' in columns:
        op.drop_column('prestamos_evaluacion', 'sector_economico_descripcion')
    if 'sector_economico_puntos' in columns:
        op.drop_column('prestamos_evaluacion', 'sector_economico_puntos')
    if 'tipo_empleo_descripcion' in columns:
        op.drop_column('prestamos_evaluacion', 'tipo_empleo_descripcion')
    if 'meses_trabajo' in columns:
        op.drop_column('prestamos_evaluacion', 'meses_trabajo')
    if 'antiguedad_trabajo_puntos' in columns:
        op.drop_column('prestamos_evaluacion', 'antiguedad_trabajo_puntos')

    # Restaurar longitud original de requisitos_adicionales
    if 'requisitos_adicionales' in columns:
        try:
            op.alter_column('prestamos_evaluacion', 'requisitos_adicionales',
                           type_=sa.String(length=200),
                           existing_type=sa.String(length=500),
                           existing_nullable=True)
        except Exception as e:
            print(f"⚠️ No se pudo restaurar columna 'requisitos_adicionales': {e}")
