"""update evaluacion 7 criterios

Revision ID: update_evaluacion_7_criterios
Revises: create_tablas_prestamos
Create Date: 2025-10-27 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'update_evaluacion_7_criterios'
down_revision = 'create_tablas_prestamos'
branch_labels = None
depends_on = None


def upgrade():
    # Agregar nuevas columnas para los 7 criterios (100 puntos)
    
    # ============================================
    # CRITERIO 1: CAPACIDAD DE PAGO (mantener ratio_endeudamiento y ratio_cobertura, ajustar valores)
    # ============================================
    # Columnas ya existen, solo actualizar descripción en comentarios
    
    # ============================================
    # CRITERIO 2: ESTABILIDAD LABORAL (23 puntos)
    # ============================================
    # Renombrar y agregar nuevas columnas
    op.add_column('prestamos_evaluacion', sa.Column('antiguedad_trabajo_puntos', sa.Numeric(5, 2), nullable=True, server_default='0'))
    op.add_column('prestamos_evaluacion', sa.Column('meses_trabajo', sa.Numeric(6, 2), nullable=True))
    
    # Mantener tipo_empleo_puntos existente, agregar nuevos campos
    op.add_column('prestamos_evaluacion', sa.Column('tipo_empleo_descripcion', sa.String(length=50), nullable=True))
    op.add_column('prestamos_evaluacion', sa.Column('sector_economico_puntos', sa.Numeric(5, 2), nullable=True, server_default='0'))
    op.add_column('prestamos_evaluacion', sa.Column('sector_economico_descripcion', sa.String(length=50), nullable=True))
    
    # ============================================
    # CRITERIO 3: REFERENCIAS PERSONALES (5 puntos)
    # ============================================
    op.add_column('prestamos_evaluacion', sa.Column('referencias_puntos', sa.Numeric(5, 2), nullable=True, server_default='0'))
    op.add_column('prestamos_evaluacion', sa.Column('referencias_descripcion', sa.String(length=50), nullable=True))
    op.add_column('prestamos_evaluacion', sa.Column('num_referencias_verificadas', sa.Integer(), nullable=True))
    
    # ============================================
    # CRITERIO 4: ARRAIGO GEOGRÁFICO (12 puntos)
    # ============================================
    op.add_column('prestamos_evaluacion', sa.Column('arraigo_vivienda_puntos', sa.Numeric(5, 2), nullable=True, server_default='0'))
    op.add_column('prestamos_evaluacion', sa.Column('arraigo_familiar_puntos', sa.Numeric(5, 2), nullable=True, server_default='0'))
    op.add_column('prestamos_evaluacion', sa.Column('arraigo_laboral_puntos', sa.Numeric(5, 2), nullable=True, server_default='0'))
    
    # ============================================
    # CRITERIO 5: PERFIL SOCIODEMOGRÁFICO (17 puntos)
    # ============================================
    op.add_column('prestamos_evaluacion', sa.Column('vivienda_puntos', sa.Numeric(5, 2), nullable=True, server_default='0'))
    op.add_column('prestamos_evaluacion', sa.Column('vivienda_descripcion', sa.String(length=50), nullable=True))
    op.add_column('prestamos_evaluacion', sa.Column('estado_civil_puntos', sa.Numeric(5, 2), nullable=True, server_default='0'))
    op.add_column('prestamos_evaluacion', sa.Column('estado_civil_descripcion', sa.String(length=50), nullable=True))
    op.add_column('prestamos_evaluacion', sa.Column('hijos_puntos', sa.Numeric(5, 2), nullable=True, server_default='0'))
    op.add_column('prestamos_evaluacion', sa.Column('hijos_descripcion', sa.String(length=50), nullable=True))
    
    # ============================================
    # CRITERIO 6: EDAD DEL CLIENTE (5 puntos)
    # ============================================
    op.add_column('prestamos_evaluacion', sa.Column('edad_puntos', sa.Numeric(5, 2), nullable=True, server_default='0'))
    op.add_column('prestamos_evaluacion', sa.Column('edad_cliente', sa.Integer(), nullable=True))
    
    # ============================================
    # ACTUALIZAR CAMPO: requisitos_adicionales (expandir de 200 a 500 caracteres)
    # ============================================
    op.alter_column('prestamos_evaluacion', 'requisitos_adicionales',
                   type_=sa.String(length=500),
                   existing_type=sa.String(length=200),
                   existing_nullable=True)
    
    # ============================================
    # ELIMINAR COLUMNAS OBSOLETAS (opcional - mantener por compatibilidad)
    # ============================================
    # NO eliminamos las columnas antiguas para mantener compatibilidad
    # Los campos antiguos serán migrados gradualmente
    

def downgrade():
    # Eliminar las nuevas columnas agregadas
    op.drop_column('prestamos_evaluacion', 'edad_cliente')
    op.drop_column('prestamos_evaluacion', 'edad_puntos')
    op.drop_column('prestamos_evaluacion', 'hijos_descripcion')
    op.drop_column('prestamos_evaluacion', 'hijos_puntos')
    op.drop_column('prestamos_evaluacion', 'estado_civil_descripcion')
    op.drop_column('prestamos_evaluacion', 'estado_civil_puntos')
    op.drop_column('prestamos_evaluacion', 'vivienda_descripcion')
    op.drop_column('prestamos_evaluacion', 'vivienda_puntos')
    op.drop_column('prestamos_evaluacion', 'arraigo_laboral_puntos')
    op.drop_column('prestamos_evaluacion', 'arraigo_familiar_puntos')
    op.drop_column('prestamos_evaluacion', 'arraigo_vivienda_puntos')
    op.drop_column('prestamos_evaluacion', 'num_referencias_verificadas')
    op.drop_column('prestamos_evaluacion', 'referencias_descripcion')
    op.drop_column('prestamos_evaluacion', 'referencias_puntos')
    op.drop_column('prestamos_evaluacion', 'sector_economico_descripcion')
    op.drop_column('prestamos_evaluacion', 'sector_economico_puntos')
    op.drop_column('prestamos_evaluacion', 'tipo_empleo_descripcion')
    op.drop_column('prestamos_evaluacion', 'meses_trabajo')
    op.drop_column('prestamos_evaluacion', 'antiguedad_trabajo_puntos')
    
    # Restaurar longitud original de requisitos_adicionales
    op.alter_column('prestamos_evaluacion', 'requisitos_adicionales',
                   type_=sa.String(length=200),
                   existing_type=sa.String(length=500),
                   existing_nullable=True)


