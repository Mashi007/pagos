"""create_ai_prompt_variables

Revision ID: 20250115_ai_prompt_variables
Revises: 9537ffbe05a6
Create Date: 2025-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '20250115_ai_prompt_variables'
down_revision = '9537ffbe05a6'  # Merge point
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
    Crear tabla ai_prompt_variables para almacenar variables personalizadas del prompt AI
    """
    connection = op.get_bind()
    inspector = inspect(connection)

    if not _table_exists(inspector, 'ai_prompt_variables'):
        op.create_table(
            'ai_prompt_variables',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('variable', sa.String(length=100), nullable=False),
            sa.Column('descripcion', sa.Text(), nullable=False),
            sa.Column('activo', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('orden', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('creado_en', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('actualizado_en', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('variable', name='uq_ai_prompt_variables_variable')
        )
        op.create_index(op.f('ix_ai_prompt_variables_id'), 'ai_prompt_variables', ['id'], unique=False)
        op.create_index('ix_ai_prompt_variables_variable', 'ai_prompt_variables', ['variable'], unique=True)
        op.create_index('ix_ai_prompt_variables_activo', 'ai_prompt_variables', ['activo'], unique=False)
        print("✅ Tabla 'ai_prompt_variables' creada exitosamente")
    else:
        print("ℹ️ Tabla 'ai_prompt_variables' ya existe, omitiendo creación...")


def downgrade():
    """Eliminar tabla ai_prompt_variables"""
    connection = op.get_bind()
    inspector = inspect(connection)

    if _table_exists(inspector, 'ai_prompt_variables'):
        try:
            # Eliminar índices primero
            indices = inspector.get_indexes('ai_prompt_variables')
            for idx in indices:
                if idx['name'] != 'ai_prompt_variables_pkey':  # No eliminar PK
                    try:
                        op.drop_index(idx['name'], table_name='ai_prompt_variables')
                    except Exception as e:
                        print(f"⚠️ Error eliminando índice {idx['name']}: {e}")

            op.drop_table('ai_prompt_variables')
            print("✅ Tabla 'ai_prompt_variables' eliminada exitosamente")
        except Exception as e:
            print(f"⚠️ Error eliminando tabla 'ai_prompt_variables': {e}")
    else:
        print("ℹ️ Tabla 'ai_prompt_variables' no existe, omitiendo eliminación...")

