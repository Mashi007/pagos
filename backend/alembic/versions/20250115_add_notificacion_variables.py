"""add_notificacion_variables_table

Revision ID: add_notificacion_variables
Revises: add_notificacion_plantillas
Create Date: 2025-01-15

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_notificacion_variables'
down_revision = 'add_notificacion_plantillas'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    # Verificar si la tabla ya existe
    if "notificacion_variables" not in inspector.get_table_names():
        # Crear tabla notificacion_variables
        op.create_table(
            'notificacion_variables',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('nombre_variable', sa.String(length=100), nullable=False),
            sa.Column('tabla', sa.String(length=50), nullable=False),
            sa.Column('campo_bd', sa.String(length=100), nullable=False),
            sa.Column('descripcion', sa.Text(), nullable=True),
            sa.Column('activa', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('fecha_creacion', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('fecha_actualizacion', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('nombre_variable')
        )
    else:
        print("Tabla 'notificacion_variables' ya existe")
    
    # Verificar índices existentes
    indexes = [idx["name"] for idx in inspector.get_indexes("notificacion_variables")] if "notificacion_variables" in inspector.get_table_names() else []
    
    # Crear índices si no existen
    if "ix_notificacion_variables_id" not in indexes:
        op.create_index(op.f('ix_notificacion_variables_id'), 'notificacion_variables', ['id'], unique=False)
    
    if "ix_notificacion_variables_nombre_variable" not in indexes:
        op.create_index(op.f('ix_notificacion_variables_nombre_variable'), 'notificacion_variables', ['nombre_variable'], unique=False)
    
    if "ix_notificacion_variables_activa" not in indexes:
        op.create_index(op.f('ix_notificacion_variables_activa'), 'notificacion_variables', ['activa'], unique=False)


def downgrade():
    # Eliminar índices
    op.drop_index(op.f('ix_notificacion_variables_activa'), table_name='notificacion_variables')
    op.drop_index(op.f('ix_notificacion_variables_nombre_variable'), table_name='notificacion_variables')
    op.drop_index(op.f('ix_notificacion_variables_id'), table_name='notificacion_variables')
    
    # Eliminar tabla
    op.drop_table('notificacion_variables')

