"""create tablas prestamos

Revision ID: create_tablas_prestamos
Revises: add_created_at_analistas_concesionarios
Create Date: 2025-10-27 02:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'create_tablas_prestamos'
down_revision = 'add_created_at_anal_conces'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = inspector.get_table_names()

    # ============================================
    # TABLA: prestamos
    # ============================================
    if 'prestamos' not in tables:
        op.create_table(
            'prestamos',
            sa.Column('id', sa.Integer(), nullable=False),

            # DATOS DEL CLIENTE
            sa.Column('cliente_id', sa.Integer(), nullable=False),
            sa.Column('cedula', sa.String(length=20), nullable=False),
            sa.Column('nombres', sa.String(length=100), nullable=False),

            # DATOS DEL PRÉSTAMO
            sa.Column('total_financiamiento', sa.Numeric(15, 2), nullable=False),
            sa.Column('fecha_requerimiento', sa.Date(), nullable=False),
            sa.Column('modalidad_pago', sa.String(length=20), nullable=False),
            sa.Column('numero_cuotas', sa.Integer(), nullable=False),
            sa.Column('cuota_periodo', sa.Numeric(15, 2), nullable=False),
            sa.Column('tasa_interes', sa.Numeric(5, 2), nullable=False, server_default='0.00'),
            sa.Column('fecha_base_calculo', sa.Date(), nullable=True),

            # PRODUCTO FINANCIERO
            sa.Column('producto', sa.String(length=100), nullable=False),
            sa.Column('producto_financiero', sa.String(length=100), nullable=False),

            # ESTADO Y APROBACIÓN
            sa.Column('estado', sa.String(length=20), nullable=False, server_default='DRAFT'),
            sa.Column('usuario_proponente', sa.String(length=100), nullable=False),
            sa.Column('usuario_aprobador', sa.String(length=100), nullable=True),
            sa.Column('observaciones', sa.Text(), nullable=True),

            # FECHAS
            sa.Column('fecha_registro', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('fecha_aprobacion', sa.TIMESTAMP(), nullable=True),
            sa.Column('fecha_actualizacion', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('informacion_desplegable', sa.Boolean(), nullable=False, server_default='false'),

            sa.PrimaryKeyConstraint('id')
        )
    else:
        print("Tabla 'prestamos' ya existe")

    # Verificar índices de prestamos
    if 'prestamos' in tables:
        indexes = [idx["name"] for idx in inspector.get_indexes("prestamos")]
        if "ix_prestamos_cliente_id" not in indexes:
            op.create_index(op.f('ix_prestamos_cliente_id'), 'prestamos', ['cliente_id'], unique=False)
        if "ix_prestamos_cedula" not in indexes:
            op.create_index(op.f('ix_prestamos_cedula'), 'prestamos', ['cedula'], unique=False)
        if "ix_prestamos_estado" not in indexes:
            op.create_index(op.f('ix_prestamos_estado'), 'prestamos', ['estado'], unique=False)

    # ============================================
    # TABLA: prestamos_auditoria
    # ============================================
    if 'prestamos_auditoria' not in tables:
        op.create_table(
            'prestamos_auditoria',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('prestamo_id', sa.Integer(), nullable=False),
            sa.Column('cedula', sa.String(length=20), nullable=False),
            sa.Column('usuario', sa.String(length=100), nullable=False),
            sa.Column('campo_modificado', sa.String(length=100), nullable=False),
            sa.Column('valor_anterior', sa.Text(), nullable=True),
            sa.Column('valor_nuevo', sa.Text(), nullable=False),
            sa.Column('accion', sa.String(length=50), nullable=False),
            sa.Column('estado_anterior', sa.String(length=20), nullable=True),
            sa.Column('estado_nuevo', sa.String(length=20), nullable=True),
            sa.Column('observaciones', sa.Text(), nullable=True),
            sa.Column('fecha_cambio', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),

            sa.PrimaryKeyConstraint('id')
        )
    else:
        print("Tabla 'prestamos_auditoria' ya existe")

    # Verificar índices de prestamos_auditoria
    if 'prestamos_auditoria' in tables:
        indexes = [idx["name"] for idx in inspector.get_indexes("prestamos_auditoria")]
        if "ix_prestamos_auditoria_prestamo_id" not in indexes:
            op.create_index(op.f('ix_prestamos_auditoria_prestamo_id'), 'prestamos_auditoria', ['prestamo_id'], unique=False)
        if "ix_prestamos_auditoria_cedula" not in indexes:
            op.create_index(op.f('ix_prestamos_auditoria_cedula'), 'prestamos_auditoria', ['cedula'], unique=False)

    # ============================================
    # TABLA: prestamos_evaluacion
    # ============================================
    if 'prestamos_evaluacion' not in tables:
        op.create_table(
            'prestamos_evaluacion',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('prestamo_id', sa.Integer(), nullable=False),

            # CRITERIO 1: Ratio de Endeudamiento (25%)
            sa.Column('ratio_endeudamiento_puntos', sa.Numeric(5, 2), nullable=False, server_default='0'),
            sa.Column('ratio_endeudamiento_calculo', sa.Numeric(10, 4), nullable=False, server_default='0'),

            # CRITERIO 2: Ratio de Cobertura (20%)
            sa.Column('ratio_cobertura_puntos', sa.Numeric(5, 2), nullable=False, server_default='0'),
            sa.Column('ratio_cobertura_calculo', sa.Numeric(10, 4), nullable=False, server_default='0'),

            # CRITERIO 3: Historial Crediticio (20%)
            sa.Column('historial_crediticio_puntos', sa.Numeric(5, 2), nullable=False, server_default='0'),
            sa.Column('historial_crediticio_descripcion', sa.String(length=50), nullable=True),

            # CRITERIO 4: Estabilidad Laboral (15%)
            sa.Column('estabilidad_laboral_puntos', sa.Numeric(5, 2), nullable=False, server_default='0'),
            sa.Column('anos_empleo', sa.Numeric(4, 2), nullable=True),

            # CRITERIO 5: Tipo de Empleo (10%)
            sa.Column('tipo_empleo_puntos', sa.Numeric(5, 2), nullable=False, server_default='0'),
            sa.Column('tipo_empleo_descripcion', sa.String(length=50), nullable=True),

            # CRITERIO 6: Enganche y Garantías (10%)
            sa.Column('enganche_garantias_puntos', sa.Numeric(5, 2), nullable=False, server_default='0'),
            sa.Column('enganche_garantias_calculo', sa.Numeric(10, 4), nullable=False, server_default='0'),

            # PUNTUACIÓN TOTAL Y CLASIFICACIÓN
            sa.Column('puntuacion_total', sa.Numeric(5, 2), nullable=False, server_default='0'),
            sa.Column('clasificacion_riesgo', sa.String(length=20), nullable=False, server_default='PENDIENTE'),
            sa.Column('decision_final', sa.String(length=20), nullable=False, server_default='PENDIENTE'),

            # CONDICIONES SEGÚN RIESGO
            sa.Column('tasa_interes_aplicada', sa.Numeric(5, 2), nullable=True),
            sa.Column('plazo_maximo', sa.Integer(), nullable=True),
            sa.Column('enganche_minimo', sa.Numeric(5, 2), nullable=True),
            sa.Column('requisitos_adicionales', sa.String(length=200), nullable=True),

            sa.PrimaryKeyConstraint('id')
        )
    else:
        print("Tabla 'prestamos_evaluacion' ya existe")

    # Verificar índices de prestamos_evaluacion
    if 'prestamos_evaluacion' in tables:
        indexes = [idx["name"] for idx in inspector.get_indexes("prestamos_evaluacion")]
        if "ix_prestamos_evaluacion_prestamo_id" not in indexes:
            op.create_index(op.f('ix_prestamos_evaluacion_prestamo_id'), 'prestamos_evaluacion', ['prestamo_id'], unique=False)

    # Verificar foreign keys existentes
    if 'prestamos' in tables:
        foreign_keys = [fk["name"] for fk in inspector.get_foreign_keys("prestamos")]
        if 'fk_prestamo_cliente' not in foreign_keys:
            try:
                op.create_foreign_key(
                    'fk_prestamo_cliente', 'prestamos', 'clientes',
                    ['cliente_id'], ['id'], ondelete='CASCADE'
                )
            except Exception as e:
                print(f"⚠️ No se pudo crear foreign key fk_prestamo_cliente: {e}")


def downgrade():
    # Eliminar índices primero
    op.drop_index(op.f('ix_prestamos_evaluacion_prestamo_id'), table_name='prestamos_evaluacion')
    op.drop_index(op.f('ix_prestamos_auditoria_cedula'), table_name='prestamos_auditoria')
    op.drop_index(op.f('ix_prestamos_auditoria_prestamo_id'), table_name='prestamos_auditoria')
    op.drop_index(op.f('ix_prestamos_estado'), table_name='prestamos')
    op.drop_index(op.f('ix_prestamos_cedula'), table_name='prestamos')
    op.drop_index(op.f('ix_prestamos_cliente_id'), table_name='prestamos')

    # Eliminar tablas
    op.drop_table('prestamos_evaluacion')
    op.drop_table('prestamos_auditoria')
    op.drop_table('prestamos')
