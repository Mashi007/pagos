"""create_ai_training_tables

Revision ID: 20250114_ai_training
Revises: 20251114_create_documentos_ai
Create Date: 2025-01-14

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '20250114_ai_training'
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
    Crear tablas para sistemas de entrenamiento AI:
    - conversaciones_ai: Conversaciones para fine-tuning
    - fine_tuning_jobs: Jobs de entrenamiento
    - documento_ai_embeddings: Embeddings vectoriales
    - modelos_riesgo: Metadatos de modelos ML
    """
    connection = op.get_bind()
    inspector = inspect(connection)

    # ============================================
    # Tabla: conversaciones_ai
    # ============================================
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

    # ============================================
    # Tabla: fine_tuning_jobs
    # ============================================
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

    # ============================================
    # Tabla: documento_ai_embeddings
    # ============================================
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

    # ============================================
    # Tabla: modelos_riesgo
    # ============================================
    if not _table_exists(inspector, 'modelos_riesgo'):
        op.create_table(
            'modelos_riesgo',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('nombre', sa.String(length=200), nullable=False),
            sa.Column('version', sa.String(length=50), nullable=False, server_default='1.0.0'),
            sa.Column('algoritmo', sa.String(length=100), nullable=False),
            sa.Column('accuracy', sa.Float(), nullable=True),
            sa.Column('precision', sa.Float(), nullable=True),
            sa.Column('recall', sa.Float(), nullable=True),
            sa.Column('f1_score', sa.Float(), nullable=True),
            sa.Column('roc_auc', sa.Float(), nullable=True),
            sa.Column('ruta_archivo', sa.String(length=500), nullable=False),
            sa.Column('total_datos_entrenamiento', sa.Integer(), nullable=True),
            sa.Column('total_datos_test', sa.Integer(), nullable=True),
            sa.Column('test_size', sa.Float(), nullable=True),
            sa.Column('random_state', sa.Integer(), nullable=True),
            sa.Column('activo', sa.Boolean(), server_default=sa.text('false'), nullable=False),
            sa.Column('usuario_id', sa.Integer(), nullable=True),
            sa.Column('descripcion', sa.Text(), nullable=True),
            sa.Column('features_usadas', sa.Text(), nullable=True),
            sa.Column('entrenado_en', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('activado_en', sa.DateTime(), nullable=True),
            sa.Column('actualizado_en', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['usuario_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_modelos_riesgo_id'), 'modelos_riesgo', ['id'], unique=False)
        op.create_index('ix_modelos_riesgo_activo', 'modelos_riesgo', ['activo'], unique=False)
        op.create_index('ix_modelos_riesgo_entrenado_en', 'modelos_riesgo', ['entrenado_en'], unique=False)
        print("✅ Tabla 'modelos_riesgo' creada exitosamente")
    else:
        print("ℹ️ Tabla 'modelos_riesgo' ya existe, omitiendo creación...")


def downgrade():
    """
    Eliminar tablas de entrenamiento AI
    """
    connection = op.get_bind()
    inspector = inspect(connection)

    # Eliminar en orden inverso (respetando foreign keys)
    tables_to_drop = [
        'modelos_riesgo',
        'documento_ai_embeddings',
        'fine_tuning_jobs',
        'conversaciones_ai',
    ]

    for table_name in tables_to_drop:
        if _table_exists(inspector, table_name):
            try:
                # Eliminar índices primero
                indices = inspector.get_indexes(table_name)
                for idx in indices:
                    try:
                        op.drop_index(idx['name'], table_name=table_name)
                    except Exception:
                        pass
                
                # Eliminar tabla
                op.drop_table(table_name)
                print(f"✅ Tabla '{table_name}' eliminada exitosamente")
            except Exception as e:
                print(f"⚠️ Error eliminando tabla '{table_name}': {e}")
        else:
            print(f"ℹ️ Tabla '{table_name}' no existe, omitiendo eliminación...")

