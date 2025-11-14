"""create_conversaciones_ai

Revision ID: 20251114_01_conversaciones_ai
Revises: 20251114_create_documentos_ai
Create Date: 2025-11-14

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '20251114_01_conversaciones_ai'
down_revision = '20251114_create_documentos_ai'
branch_labels = None
depends_on = None


def _table_exists(inspector, table_name: str) -> bool:
    """Verifica si una tabla existe"""
    try:
        return table_name in inspector.get_table_names()
    except Exception:
        return False


def upgrade():
    """
    Crear tabla conversaciones_ai para almacenar conversaciones para fine-tuning
    """
    connection = op.get_bind()
    inspector = inspect(connection)

    if not _table_exists(inspector, 'conversaciones_ai'):
        op.create_table(
            'conversaciones_ai',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('pregunta', sa.Text(), nullable=False),
            sa.Column('respuesta', sa.Text(), nullable=False),
            sa.Column('contexto_usado', sa.Text(), nullable=True),
            sa.Column('documentos_usados', sa.String(length=500), nullable=True),
            sa.Column('modelo_usado', sa.String(length=100), nullable=True),
            sa.Column('tokens_usados', sa.Integer(), nullable=True),
            sa.Column('tiempo_respuesta', sa.Integer(), nullable=True),
            sa.Column('calificacion', sa.Integer(), nullable=True),
            sa.Column('feedback', sa.Text(), nullable=True),
            sa.Column('usuario_id', sa.Integer(), nullable=True),
            sa.Column('cliente_id', sa.Integer(), nullable=True),
            sa.Column('prestamo_id', sa.Integer(), nullable=True),
            sa.Column('pago_id', sa.Integer(), nullable=True),
            sa.Column('cuota_id', sa.Integer(), nullable=True),
            sa.Column('creado_en', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('actualizado_en', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['usuario_id'], ['users.id'], ),
            sa.ForeignKeyConstraint(['cliente_id'], ['clientes.id'], ),
            sa.ForeignKeyConstraint(['prestamo_id'], ['prestamos.id'], ),
            sa.ForeignKeyConstraint(['pago_id'], ['pagos.id'], ),
            sa.ForeignKeyConstraint(['cuota_id'], ['cuotas.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_conversaciones_ai_id'), 'conversaciones_ai', ['id'], unique=False)
        op.create_index('ix_conversaciones_ai_creado_en', 'conversaciones_ai', ['creado_en'], unique=False)
        op.create_index('ix_conversaciones_ai_calificacion', 'conversaciones_ai', ['calificacion'], unique=False)
        op.create_index('ix_conversaciones_ai_cliente_id', 'conversaciones_ai', ['cliente_id'], unique=False)
        op.create_index('ix_conversaciones_ai_prestamo_id', 'conversaciones_ai', ['prestamo_id'], unique=False)
        op.create_index('ix_conversaciones_ai_pago_id', 'conversaciones_ai', ['pago_id'], unique=False)
        op.create_index('ix_conversaciones_ai_cuota_id', 'conversaciones_ai', ['cuota_id'], unique=False)
        print("✅ Tabla 'conversaciones_ai' creada exitosamente")
    else:
        print("ℹ️ Tabla 'conversaciones_ai' ya existe, omitiendo creación...")


def downgrade():
    """Eliminar tabla conversaciones_ai"""
    connection = op.get_bind()
    inspector = inspect(connection)

    if _table_exists(inspector, 'conversaciones_ai'):
        try:
            # Eliminar índices primero
            indices = inspector.get_indexes('conversaciones_ai')
            for idx in indices:
                try:
                    op.drop_index(idx['name'], table_name='conversaciones_ai')
                except Exception:
                    pass
            
            # Eliminar tabla
            op.drop_table('conversaciones_ai')
            print("✅ Tabla 'conversaciones_ai' eliminada exitosamente")
        except Exception as e:
            print(f"⚠️ Error eliminando tabla 'conversaciones_ai': {e}")
    else:
        print("ℹ️ Tabla 'conversaciones_ai' no existe, omitiendo eliminación...")

