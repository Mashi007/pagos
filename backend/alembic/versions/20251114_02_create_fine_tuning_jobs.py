"""create_fine_tuning_jobs

Revision ID: 20251114_02_fine_tuning_jobs
Revises: 20251114_01_conversaciones_ai
Create Date: 2025-11-14

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '20251114_02_fine_tuning_jobs'
down_revision = '20251114_01_conversaciones_ai'
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
    Crear tabla fine_tuning_jobs para almacenar jobs de entrenamiento de OpenAI
    """
    connection = op.get_bind()
    inspector = inspect(connection)

    if not _table_exists(inspector, 'fine_tuning_jobs'):
        op.create_table(
            'fine_tuning_jobs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('openai_job_id', sa.String(length=100), nullable=False),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
            sa.Column('modelo_base', sa.String(length=100), nullable=False),
            sa.Column('modelo_entrenado', sa.String(length=200), nullable=True),
            sa.Column('archivo_entrenamiento', sa.String(length=500), nullable=True),
            sa.Column('total_conversaciones', sa.Integer(), nullable=True),
            sa.Column('progreso', sa.Float(), nullable=True),
            sa.Column('error', sa.Text(), nullable=True),
            sa.Column('epochs', sa.Integer(), nullable=True),
            sa.Column('learning_rate', sa.Float(), nullable=True),
            sa.Column('creado_en', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('completado_en', sa.DateTime(), nullable=True),
            sa.Column('actualizado_en', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('openai_job_id')
        )
        op.create_index(op.f('ix_fine_tuning_jobs_id'), 'fine_tuning_jobs', ['id'], unique=False)
        op.create_index('ix_fine_tuning_jobs_openai_job_id', 'fine_tuning_jobs', ['openai_job_id'], unique=True)
        op.create_index('ix_fine_tuning_jobs_status', 'fine_tuning_jobs', ['status'], unique=False)
        op.create_index('ix_fine_tuning_jobs_creado_en', 'fine_tuning_jobs', ['creado_en'], unique=False)
        print("✅ Tabla 'fine_tuning_jobs' creada exitosamente")
    else:
        print("ℹ️ Tabla 'fine_tuning_jobs' ya existe, omitiendo creación...")


def downgrade():
    """Eliminar tabla fine_tuning_jobs"""
    connection = op.get_bind()
    inspector = inspect(connection)

    if _table_exists(inspector, 'fine_tuning_jobs'):
        try:
            # Eliminar índices primero
            indices = inspector.get_indexes('fine_tuning_jobs')
            for idx in indices:
                try:
                    op.drop_index(idx['name'], table_name='fine_tuning_jobs')
                except Exception:
                    pass

            # Eliminar tabla
            op.drop_table('fine_tuning_jobs')
            print("✅ Tabla 'fine_tuning_jobs' eliminada exitosamente")
        except Exception as e:
            print(f"⚠️ Error eliminando tabla 'fine_tuning_jobs': {e}")
    else:
        print("ℹ️ Tabla 'fine_tuning_jobs' no existe, omitiendo eliminación...")

