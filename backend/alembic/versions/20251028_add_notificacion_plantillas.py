"""add_notificacion_plantillas_table

Revision ID: add_notificacion_plantillas
Revises: 20251028_pagos
Create Date: 2025-10-28

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_notificacion_plantillas'
down_revision = '20251028_pagos'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    # Verificar si la tabla ya existe
    if "notificacion_plantillas" not in inspector.get_table_names():
        # Crear tabla notificacion_plantillas
        op.create_table(
            'notificacion_plantillas',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('nombre', sa.String(length=100), nullable=False),
            sa.Column('descripcion', sa.Text(), nullable=True),
            sa.Column('tipo', sa.String(length=20), nullable=False),
            sa.Column('asunto', sa.String(length=200), nullable=False),
            sa.Column('cuerpo', sa.Text(), nullable=False),
            sa.Column('variables_disponibles', sa.Text(), nullable=True),
            sa.Column('activa', sa.Boolean(), nullable=False),
            sa.Column('zona_horaria', sa.String(length=50), nullable=False),
            sa.Column('fecha_creacion', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('fecha_actualizacion', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('nombre')
        )
    else:
        print("Tabla 'notificacion_plantillas' ya existe")

    # Verificar índices existentes
    indexes = [idx["name"] for idx in inspector.get_indexes("notificacion_plantillas")] if "notificacion_plantillas" in inspector.get_table_names() else []

    if "ix_notificacion_plantillas_id" not in indexes:
        op.create_index(op.f('ix_notificacion_plantillas_id'), 'notificacion_plantillas', ['id'], unique=False)


def downgrade():
    # Eliminar tabla
    op.drop_index(op.f('ix_notificacion_plantillas_id'), table_name='notificacion_plantillas')
    op.drop_table('notificacion_plantillas')
