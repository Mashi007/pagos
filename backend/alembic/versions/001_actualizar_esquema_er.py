"""Actualizar esquema para coincidir con diagrama ER

Revision ID: 001_actualizar_esquema_er
Revises: 
Create Date: 2025-10-12 17:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_actualizar_esquema_er'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Aplicar cambios a la base de datos."""
    
    # Crear tabla de configuración
    op.create_table('configuracion',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('clave', sa.String(length=100), nullable=False),
        sa.Column('valor', sa.JSON(), nullable=False),
        sa.Column('tipo', sa.String(length=50), nullable=False),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('clave')
    )
    op.create_index(op.f('ix_configuracion_id'), 'configuracion', ['id'], unique=False)
    op.create_index(op.f('ix_configuracion_clave'), 'configuracion', ['clave'], unique=True)
    op.create_index(op.f('ix_configuracion_tipo'), 'configuracion', ['tipo'], unique=False)
    
    # Crear tabla de conciliación
    op.create_table('conciliacion',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pago_id', sa.Integer(), nullable=False),
        sa.Column('fecha_carga', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ref_bancaria', sa.String(length=100), nullable=False),
        sa.Column('monto_banco', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('estado_match', sa.String(length=20), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=True),
        sa.Column('observaciones', sa.Text(), nullable=True),
        sa.Column('tipo_match', sa.String(length=20), nullable=True),
        sa.Column('confianza_match', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['pago_id'], ['pagos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_conciliacion_id'), 'conciliacion', ['id'], unique=False)
    op.create_index(op.f('ix_conciliacion_pago_id'), 'conciliacion', ['pago_id'], unique=False)
    op.create_index(op.f('ix_conciliacion_ref_bancaria'), 'conciliacion', ['ref_bancaria'], unique=False)
    op.create_index(op.f('ix_conciliacion_estado_match'), 'conciliacion', ['estado_match'], unique=False)
    op.create_index(op.f('ix_conciliacion_usuario_id'), 'conciliacion', ['usuario_id'], unique=False)
    
    # Agregar campos faltantes a la tabla clientes
    op.add_column('clientes', sa.Column('estado_caso', sa.String(length=50), nullable=True))
    op.add_column('clientes', sa.Column('modelo_vehiculo', sa.String(length=100), nullable=True))
    op.add_column('clientes', sa.Column('analista_id', sa.Integer(), nullable=True))
    op.add_column('clientes', sa.Column('concesionario', sa.String(length=100), nullable=True))
    op.add_column('clientes', sa.Column('fecha_pago_ini', sa.Date(), nullable=True))
    op.add_column('clientes', sa.Column('total_financia', sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column('clientes', sa.Column('cuota_inicial', sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column('clientes', sa.Column('fecha_entrega', sa.Date(), nullable=True))
    op.add_column('clientes', sa.Column('amortizaciones', sa.Integer(), nullable=True))
    op.add_column('clientes', sa.Column('modalidad_finan', sa.String(length=20), nullable=True))
    op.add_column('clientes', sa.Column('requiere_actual', sa.Boolean(), nullable=True))
    
    # Crear foreign key para analista_id
    op.create_foreign_key('fk_clientes_analista_id', 'clientes', 'usuarios', ['analista_id'], ['id'])
    op.create_index(op.f('ix_clientes_analista_id'), 'clientes', ['analista_id'], unique=False)
    
    # Insertar configuraciones por defecto
    op.execute("""
        INSERT INTO configuracion (clave, valor, tipo, descripcion) VALUES
        ('TASA_INTERES_BASE', '15.0', 'TASA', 'Tasa de interés base anual (%)'),
        ('TASA_MORA', '2.0', 'TASA', 'Tasa de mora mensual (%)'),
        ('MONTO_MINIMO_PRESTAMO', '100.0', 'LIMITE', 'Monto mínimo de préstamo'),
        ('MONTO_MAXIMO_PRESTAMO', '50000.0', 'LIMITE', 'Monto máximo de préstamo'),
        ('PLAZO_MINIMO_MESES', '1', 'LIMITE', 'Plazo mínimo en meses'),
        ('PLAZO_MAXIMO_MESES', '60', 'LIMITE', 'Plazo máximo en meses'),
        ('DIAS_PREVIOS_RECORDATORIO', '3', 'NOTIFICACION', 'Días antes del vencimiento para recordatorio'),
        ('DIAS_MORA_ALERTA', '15', 'NOTIFICACION', 'Días de mora para enviar alerta'),
        ('NOMBRE_EMPRESA', '"Sistema de Préstamos y Cobranza"', 'EMPRESA', 'Nombre de la empresa'),
        ('EMAIL_EMPRESA', '"info@prestamos.com"', 'EMPRESA', 'Email de contacto'),
        ('TELEFONO_EMPRESA', '"+593 99 999 9999"', 'EMPRESA', 'Teléfono de contacto')
    """)


def downgrade() -> None:
    """Revertir cambios de la base de datos."""
    
    # Eliminar foreign key y campos agregados a clientes
    op.drop_constraint('fk_clientes_analista_id', 'clientes', type_='foreignkey')
    op.drop_index(op.f('ix_clientes_analista_id'), table_name='clientes')
    
    op.drop_column('clientes', 'requiere_actual')
    op.drop_column('clientes', 'modalidad_finan')
    op.drop_column('clientes', 'amortizaciones')
    op.drop_column('clientes', 'fecha_entrega')
    op.drop_column('clientes', 'cuota_inicial')
    op.drop_column('clientes', 'total_financia')
    op.drop_column('clientes', 'fecha_pago_ini')
    op.drop_column('clientes', 'concesionario')
    op.drop_column('clientes', 'analista_id')
    op.drop_column('clientes', 'modelo_vehiculo')
    op.drop_column('clientes', 'estado_caso')
    
    # Eliminar tabla conciliacion
    op.drop_index(op.f('ix_conciliacion_usuario_id'), table_name='conciliacion')
    op.drop_index(op.f('ix_conciliacion_estado_match'), table_name='conciliacion')
    op.drop_index(op.f('ix_conciliacion_ref_bancaria'), table_name='conciliacion')
    op.drop_index(op.f('ix_conciliacion_pago_id'), table_name='conciliacion')
    op.drop_index(op.f('ix_conciliacion_id'), table_name='conciliacion')
    op.drop_table('conciliacion')
    
    # Eliminar tabla configuracion
    op.drop_index(op.f('ix_configuracion_tipo'), table_name='configuracion')
    op.drop_index(op.f('ix_configuracion_clave'), table_name='configuracion')
    op.drop_index(op.f('ix_configuracion_id'), table_name='configuracion')
    op.drop_table('configuracion')
