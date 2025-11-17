"""create_documentos_ai_table

Revision ID: 20251114_create_documentos_ai
Revises: 20251109_endpoint_optimization_indexes
Create Date: 2025-11-14

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '20251114_create_documentos_ai'
down_revision = '20251109_endpoint_optimization_indexes'
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
    Crear tabla documentos_ai para almacenar documentos de contexto para AI
    """
    connection = op.get_bind()
    inspector = inspect(connection)

    # Verificar si la tabla ya existe
    if not _table_exists(inspector, 'documentos_ai'):
        # Crear tabla documentos_ai
        op.create_table(
            'documentos_ai',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('titulo', sa.String(length=255), nullable=False),
            sa.Column('descripcion', sa.Text(), nullable=True),

            # Información del archivo
            sa.Column('nombre_archivo', sa.String(length=255), nullable=False),
            sa.Column('tipo_archivo', sa.String(length=50), nullable=False),  # pdf, txt, docx, etc.
            sa.Column('ruta_archivo', sa.String(length=500), nullable=False),  # Ruta donde se almacena el archivo
            sa.Column('tamaño_bytes', sa.Integer(), nullable=True),  # Nota: PostgreSQL maneja caracteres especiales automáticamente

            # Contenido procesado
            sa.Column('contenido_texto', sa.Text(), nullable=True),  # Texto extraído del documento
            sa.Column('contenido_procesado', sa.Boolean(), server_default=sa.text('false'), nullable=False),  # Si ya se procesó el contenido

            # Estado
            sa.Column('activo', sa.Boolean(), server_default=sa.text('true'), nullable=False),

            # Auditoría
            sa.Column('creado_en', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('actualizado_en', sa.DateTime(), server_default=sa.text('now()'), nullable=False),

            sa.PrimaryKeyConstraint('id')
        )

        # Crear índices
        op.create_index(op.f('ix_documentos_ai_id'), 'documentos_ai', ['id'], unique=False)
        op.create_index('ix_documentos_ai_activo', 'documentos_ai', ['activo'], unique=False)
        op.create_index('ix_documentos_ai_contenido_procesado', 'documentos_ai', ['contenido_procesado'], unique=False)
        op.create_index('ix_documentos_ai_tipo_archivo', 'documentos_ai', ['tipo_archivo'], unique=False)

        print("✅ Tabla 'documentos_ai' creada exitosamente")
    else:
        print("ℹ️ Tabla 'documentos_ai' ya existe, omitiendo creación...")


def downgrade():
    """
    Eliminar tabla documentos_ai
    """
    connection = op.get_bind()
    inspector = inspect(connection)

    if _table_exists(inspector, 'documentos_ai'):
        # Eliminar índices primero
        try:
            op.drop_index('ix_documentos_ai_tipo_archivo', table_name='documentos_ai')
        except Exception:
            pass

        try:
            op.drop_index('ix_documentos_ai_contenido_procesado', table_name='documentos_ai')
        except Exception:
            pass

        try:
            op.drop_index('ix_documentos_ai_activo', table_name='documentos_ai')
        except Exception:
            pass

        try:
            op.drop_index(op.f('ix_documentos_ai_id'), table_name='documentos_ai')
        except Exception:
            pass

        # Eliminar tabla
        op.drop_table('documentos_ai')
        print("✅ Tabla 'documentos_ai' eliminada exitosamente")
    else:
        print("ℹ️ Tabla 'documentos_ai' no existe, omitiendo eliminación...")

