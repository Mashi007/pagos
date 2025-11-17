"""create_conversaciones_whatsapp

Revision ID: 20250117_conversaciones_whatsapp
Revises: 20251114_05_modelos_impago_cuotas
Create Date: 2025-01-17

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '20250117_conversaciones_whatsapp'
down_revision = '20251114_05_modelos_impago_cuotas'
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
    Crear tabla conversaciones_whatsapp para almacenar conversaciones de WhatsApp en el CRM
    """
    connection = op.get_bind()
    inspector = inspect(connection)

    if not _table_exists(inspector, 'conversaciones_whatsapp'):
        op.create_table(
            'conversaciones_whatsapp',
            sa.Column('id', sa.Integer(), nullable=False),
            
            # Información del mensaje
            sa.Column('message_id', sa.String(length=100), nullable=True),  # ID de Meta
            sa.Column('from_number', sa.String(length=20), nullable=False),  # Número que envía
            sa.Column('to_number', sa.String(length=20), nullable=False),  # Número que recibe
            sa.Column('message_type', sa.String(length=20), nullable=False),  # text, image, document, etc.
            sa.Column('body', sa.Text(), nullable=True),  # Contenido del mensaje
            sa.Column('timestamp', sa.DateTime(), nullable=False),  # Timestamp de Meta
            
            # Dirección del mensaje
            sa.Column('direccion', sa.String(length=10), nullable=False),  # INBOUND o OUTBOUND
            
            # Relación con cliente
            sa.Column('cliente_id', sa.Integer(), nullable=True),
            
            # Estado y procesamiento
            sa.Column('procesado', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('respuesta_enviada', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('respuesta_id', sa.Integer(), nullable=True),  # ID de la respuesta (self-reference)
            
            # Información de respuesta del bot
            sa.Column('respuesta_bot', sa.Text(), nullable=True),  # Respuesta generada por el bot
            sa.Column('respuesta_meta_id', sa.String(length=100), nullable=True),  # ID de mensaje de respuesta en Meta
            
            # Errores
            sa.Column('error', sa.Text(), nullable=True),  # Error al procesar o responder
            
            # Auditoría
            sa.Column('creado_en', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('actualizado_en', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            
            # Constraints
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['cliente_id'], ['clientes.id'], ),
            sa.ForeignKeyConstraint(['respuesta_id'], ['conversaciones_whatsapp.id'], ),
        )
        
        # Crear índices
        op.create_index(op.f('ix_conversaciones_whatsapp_id'), 'conversaciones_whatsapp', ['id'], unique=False)
        op.create_index('ix_conversaciones_whatsapp_message_id', 'conversaciones_whatsapp', ['message_id'], unique=True)
        op.create_index('ix_conversaciones_whatsapp_from_number', 'conversaciones_whatsapp', ['from_number'], unique=False)
        op.create_index('ix_conversaciones_whatsapp_timestamp', 'conversaciones_whatsapp', ['timestamp'], unique=False)
        op.create_index('ix_conversaciones_whatsapp_cliente_id', 'conversaciones_whatsapp', ['cliente_id'], unique=False)
        op.create_index('ix_conversaciones_whatsapp_creado_en', 'conversaciones_whatsapp', ['creado_en'], unique=False)
        
        print("✅ Tabla 'conversaciones_whatsapp' creada exitosamente")
    else:
        print("ℹ️ Tabla 'conversaciones_whatsapp' ya existe, omitiendo creación...")


def downgrade():
    """Eliminar tabla conversaciones_whatsapp"""
    connection = op.get_bind()
    inspector = inspect(connection)

    if _table_exists(inspector, 'conversaciones_whatsapp'):
        try:
            # Eliminar índices primero
            indices = inspector.get_indexes('conversaciones_whatsapp')
            for idx in indices:
                try:
                    op.drop_index(idx['name'], table_name='conversaciones_whatsapp')
                except Exception:
                    pass
            
            # Eliminar tabla
            op.drop_table('conversaciones_whatsapp')
            print("✅ Tabla 'conversaciones_whatsapp' eliminada exitosamente")
        except Exception as e:
            print(f"⚠️ Error eliminando tabla 'conversaciones_whatsapp': {e}")
    else:
        print("ℹ️ Tabla 'conversaciones_whatsapp' no existe, omitiendo eliminación...")

