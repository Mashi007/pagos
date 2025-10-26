"""create_logos_table

Revision ID: 018_create_logos_table
Revises: 017_add_is_admin_column
Create Date: 2025-10-26 03:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '018_create_logos_table'
down_revision = '017_add_is_admin_column'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Crear tabla logos
    op.create_table(
        'logos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.Column('archivo', sa.LargeBinary(), nullable=False),
        sa.Column('tipo_mime', sa.String(length=50), nullable=False, server_default='image/png'),
        sa.Column('fecha_upload', sa.DateTime(), nullable=False),
        sa.Column('subido_por', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_logos_id'), 'logos', ['id'], unique=False)
    op.create_index(op.f('ix_logos_nombre'), 'logos', ['nombre'], unique=True)


def downgrade() -> None:
    # Eliminar tabla logos
    op.drop_index(op.f('ix_logos_nombre'), table_name='logos')
    op.drop_index(op.f('ix_logos_id'), table_name='logos')
    op.drop_table('logos')

