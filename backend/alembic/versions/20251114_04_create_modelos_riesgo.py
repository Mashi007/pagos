"""create_modelos_riesgo

Revision ID: 20251114_04_modelos_riesgo
Revises: 20251114_03_documento_ai_embeddings
Create Date: 2025-11-14

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '20251114_04_modelos_riesgo'
down_revision = '20251114_03_documento_ai_embeddings'
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
    Crear tabla modelos_riesgo para almacenar metadatos de modelos ML de riesgo crediticio
    """
    connection = op.get_bind()
    inspector = inspect(connection)

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
    """Eliminar tabla modelos_riesgo"""
    connection = op.get_bind()
    inspector = inspect(connection)

    if _table_exists(inspector, 'modelos_riesgo'):
        try:
            # Eliminar índices primero
            indices = inspector.get_indexes('modelos_riesgo')
            for idx in indices:
                try:
                    op.drop_index(idx['name'], table_name='modelos_riesgo')
                except Exception:
                    pass
            
            # Eliminar tabla
            op.drop_table('modelos_riesgo')
            print("✅ Tabla 'modelos_riesgo' eliminada exitosamente")
        except Exception as e:
            print(f"⚠️ Error eliminando tabla 'modelos_riesgo': {e}")
    else:
        print("ℹ️ Tabla 'modelos_riesgo' no existe, omitiendo eliminación...")

