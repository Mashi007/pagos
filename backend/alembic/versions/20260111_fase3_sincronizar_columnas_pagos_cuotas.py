"""FASE 3: Sincronizar columnas faltantes en pagos y cuotas

Revision ID: 20260111_fase3_sync
Revises: 20260110_fix_indice_pagos_fecha_registro
Create Date: 2026-01-11

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260111_fase3_sync'
down_revision = '20260110_fix_indice_pagos_fecha_registro'
branch_labels = None
depends_on = None


def upgrade():
    """
    FASE 3: Agregar columnas faltantes en tablas pagos y cuotas
    para sincronizar modelo ORM con base de datos.
    """
    connection = op.get_bind()
    inspector = inspect(connection)

    # ============================================
    # TABLA PAGOS: Agregar 21 columnas faltantes
    # ============================================
    if 'pagos' in inspector.get_table_names():
        columns = {col['name']: col for col in inspector.get_columns('pagos')}
        
        # Información bancaria y método de pago
        if 'banco' not in columns:
            op.add_column('pagos', sa.Column('banco', sa.String(length=100), nullable=True))
            print("✅ Columna 'banco' agregada a tabla pagos")
        
        if 'metodo_pago' not in columns:
            op.add_column('pagos', sa.Column('metodo_pago', sa.String(length=50), nullable=True))
            print("✅ Columna 'metodo_pago' agregada a tabla pagos")
        
        if 'tipo_pago' not in columns:
            op.add_column('pagos', sa.Column('tipo_pago', sa.String(length=50), nullable=True))
            print("✅ Columna 'tipo_pago' agregada a tabla pagos")
        
        # Códigos y referencias
        if 'codigo_pago' not in columns:
            op.add_column('pagos', sa.Column('codigo_pago', sa.String(length=30), nullable=True))
            print("✅ Columna 'codigo_pago' agregada a tabla pagos")
        
        if 'numero_operacion' not in columns:
            op.add_column('pagos', sa.Column('numero_operacion', sa.String(length=50), nullable=True))
            print("✅ Columna 'numero_operacion' agregada a tabla pagos")
        
        if 'referencia_pago' not in columns:
            op.add_column('pagos', sa.Column('referencia_pago', sa.String(length=100), nullable=True))
            print("✅ Columna 'referencia_pago' agregada a tabla pagos")
        
        if 'comprobante' not in columns:
            op.add_column('pagos', sa.Column('comprobante', sa.String(length=200), nullable=True))
            print("✅ Columna 'comprobante' agregada a tabla pagos")
        
        # Documentación
        if 'documento' not in columns:
            op.add_column('pagos', sa.Column('documento', sa.String(length=50), nullable=True))
            print("✅ Columna 'documento' agregada a tabla pagos")
        
        # Montos detallados
        if 'monto' not in columns:
            op.add_column('pagos', sa.Column('monto', sa.Numeric(12, 2), nullable=True))
            print("✅ Columna 'monto' agregada a tabla pagos")
        
        if 'monto_capital' not in columns:
            op.add_column('pagos', sa.Column('monto_capital', sa.Numeric(12, 2), nullable=True))
            print("✅ Columna 'monto_capital' agregada a tabla pagos")
        
        if 'monto_interes' not in columns:
            op.add_column('pagos', sa.Column('monto_interes', sa.Numeric(12, 2), nullable=True))
            print("✅ Columna 'monto_interes' agregada a tabla pagos")
        
        if 'monto_cuota_programado' not in columns:
            op.add_column('pagos', sa.Column('monto_cuota_programado', sa.Numeric(12, 2), nullable=True))
            print("✅ Columna 'monto_cuota_programado' agregada a tabla pagos")
        
        if 'monto_mora' not in columns:
            op.add_column('pagos', sa.Column('monto_mora', sa.Numeric(12, 2), nullable=True))
            print("✅ Columna 'monto_mora' agregada a tabla pagos")
        
        if 'monto_total' not in columns:
            op.add_column('pagos', sa.Column('monto_total', sa.Numeric(12, 2), nullable=True))
            print("✅ Columna 'monto_total' agregada a tabla pagos")
        
        if 'descuento' not in columns:
            op.add_column('pagos', sa.Column('descuento', sa.Numeric(12, 2), nullable=True))
            print("✅ Columna 'descuento' agregada a tabla pagos")
        
        # Información de mora y vencimiento
        if 'dias_mora' not in columns:
            op.add_column('pagos', sa.Column('dias_mora', sa.Integer(), nullable=True))
            print("✅ Columna 'dias_mora' agregada a tabla pagos")
        
        if 'tasa_mora' not in columns:
            op.add_column('pagos', sa.Column('tasa_mora', sa.Numeric(5, 2), nullable=True))
            print("✅ Columna 'tasa_mora' agregada a tabla pagos")
        
        if 'fecha_vencimiento' not in columns:
            op.add_column('pagos', sa.Column('fecha_vencimiento', sa.DateTime(), nullable=True))
            print("✅ Columna 'fecha_vencimiento' agregada a tabla pagos")
        
        # Fechas y horas adicionales
        if 'hora_pago' not in columns:
            op.add_column('pagos', sa.Column('hora_pago', sa.String(length=10), nullable=True))
            print("✅ Columna 'hora_pago' agregada a tabla pagos")
        
        if 'creado_en' not in columns:
            op.add_column('pagos', sa.Column('creado_en', sa.DateTime(), nullable=True))
            print("✅ Columna 'creado_en' agregada a tabla pagos")
        
        # Observaciones adicionales (ya existe como 'notas', pero agregamos 'observaciones' si no existe)
        if 'observaciones' not in columns:
            op.add_column('pagos', sa.Column('observaciones', sa.Text(), nullable=True))
            print("✅ Columna 'observaciones' agregada a tabla pagos")
    else:
        print("⚠️ Tabla 'pagos' no existe, saltando migración")

    # ============================================
    # TABLA CUOTAS: Agregar 2 columnas faltantes
    # ============================================
    if 'cuotas' in inspector.get_table_names():
        columns = {col['name']: col for col in inspector.get_columns('cuotas')}
        
        if 'creado_en' not in columns:
            op.add_column('cuotas', sa.Column('creado_en', sa.Date(), nullable=True))
            print("✅ Columna 'creado_en' agregada a tabla cuotas")
        
        if 'actualizado_en' not in columns:
            op.add_column('cuotas', sa.Column('actualizado_en', sa.Date(), nullable=True))
            print("✅ Columna 'actualizado_en' agregada a tabla cuotas")
    else:
        print("⚠️ Tabla 'cuotas' no existe, saltando migración")


def downgrade():
    """Eliminar columnas agregadas en upgrade"""
    connection = op.get_bind()
    inspector = inspect(connection)

    # Eliminar columnas de pagos
    if 'pagos' in inspector.get_table_names():
        columns = {col['name']: col for col in inspector.get_columns('pagos')}
        
        columnas_a_eliminar = [
            'banco', 'metodo_pago', 'tipo_pago', 'codigo_pago', 'numero_operacion',
            'referencia_pago', 'comprobante', 'documento', 'monto', 'monto_capital',
            'monto_interes', 'monto_cuota_programado', 'monto_mora', 'monto_total',
            'descuento', 'dias_mora', 'tasa_mora', 'fecha_vencimiento', 'hora_pago',
            'creado_en', 'observaciones'
        ]
        
        for col_name in columnas_a_eliminar:
            if col_name in columns:
                op.drop_column('pagos', col_name)
                print(f"✅ Columna '{col_name}' eliminada de tabla pagos")

    # Eliminar columnas de cuotas
    if 'cuotas' in inspector.get_table_names():
        columns = {col['name']: col for col in inspector.get_columns('cuotas')}
        
        if 'creado_en' in columns:
            op.drop_column('cuotas', 'creado_en')
            print("✅ Columna 'creado_en' eliminada de tabla cuotas")
        
        if 'actualizado_en' in columns:
            op.drop_column('cuotas', 'actualizado_en')
            print("✅ Columna 'actualizado_en' eliminada de tabla cuotas")
