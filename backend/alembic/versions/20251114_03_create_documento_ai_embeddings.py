"""create_documento_ai_embeddings

Revision ID: 20251114_03_documento_ai_embeddings
Revises: 20251114_02_fine_tuning_jobs
Create Date: 2025-11-14

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '20251114_03_documento_ai_embeddings'
down_revision = '20251114_02_fine_tuning_jobs'
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
    Crear tabla documento_ai_embeddings para almacenar embeddings vectoriales de documentos
    Nota: Depende de la tabla documentos_ai (debe existir previamente)
    """
    connection = op.get_bind()
    inspector = inspect(connection)

    # Verificar que documentos_ai existe
    if not _table_exists(inspector, 'documentos_ai'):
        raise Exception("La tabla 'documentos_ai' debe existir antes de crear 'documento_ai_embeddings'")

    if not _table_exists(inspector, 'documento_ai_embeddings'):
        op.create_table(
            'documento_ai_embeddings',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('documento_id', sa.Integer(), nullable=False),
            sa.Column('embedding', sa.Text(), nullable=False),  # JSON array
            sa.Column('chunk_index', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('texto_chunk', sa.Text(), nullable=True),
            sa.Column('modelo_embedding', sa.String(length=100), nullable=True),
            sa.Column('dimensiones', sa.Integer(), nullable=True),
            sa.Column('creado_en', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('actualizado_en', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['documento_id'], ['documentos_ai.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_documento_ai_embeddings_id'), 'documento_ai_embeddings', ['id'], unique=False)
        op.create_index('ix_documento_ai_embeddings_documento_id', 'documento_ai_embeddings', ['documento_id'], unique=False)
        op.create_index('ix_documento_ai_embeddings_creado_en', 'documento_ai_embeddings', ['creado_en'], unique=False)
        print("✅ Tabla 'documento_ai_embeddings' creada exitosamente")
    else:
        print("ℹ️ Tabla 'documento_ai_embeddings' ya existe, omitiendo creación...")


def downgrade():
    """Eliminar tabla documento_ai_embeddings"""
    connection = op.get_bind()
    inspector = inspect(connection)

    if _table_exists(inspector, 'documento_ai_embeddings'):
        try:
            # Eliminar índices primero
            indices = inspector.get_indexes('documento_ai_embeddings')
            for idx in indices:
                try:
                    op.drop_index(idx['name'], table_name='documento_ai_embeddings')
                except Exception:
                    pass
            
            # Eliminar tabla
            op.drop_table('documento_ai_embeddings')
            print("✅ Tabla 'documento_ai_embeddings' eliminada exitosamente")
        except Exception as e:
            print(f"⚠️ Error eliminando tabla 'documento_ai_embeddings': {e}")
    else:
        print("ℹ️ Tabla 'documento_ai_embeddings' no existe, omitiendo eliminación...")

