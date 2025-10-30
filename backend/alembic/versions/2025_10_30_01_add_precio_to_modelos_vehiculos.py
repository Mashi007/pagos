"""add precio and audit fields to modelos_vehiculos

Revision ID: 20251030_modelos_vehiculos_precio
Revises: 20251030_actualizar_catalogos
Create Date: 2025-10-30
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251030_modelos_vehiculos_precio'
down_revision = '20251030_actualizar_catalogos'
branch_labels = None
depends_on = None


def upgrade() -> None:
    try:
        # Agregar columnas si no existen
        conn = op.get_bind()
        inspector = sa.inspect(conn)
        cols = {c['name'] for c in inspector.get_columns('modelos_vehiculos')}

        if 'precio' not in cols:
            op.add_column('modelos_vehiculos', sa.Column('precio', sa.Numeric(15, 2), nullable=True))
        if 'fecha_actualizacion' not in cols:
            op.add_column('modelos_vehiculos', sa.Column('fecha_actualizacion', sa.DateTime(timezone=True), nullable=True))
        if 'actualizado_por' not in cols:
            op.add_column('modelos_vehiculos', sa.Column('actualizado_por', sa.String(length=100), nullable=True))
    except Exception:
        # Tabla podría no existir aún en algunos entornos; ignorar de forma segura
        pass


def downgrade() -> None:
    try:
        conn = op.get_bind()
        inspector = sa.inspect(conn)
        cols = {c['name'] for c in inspector.get_columns('modelos_vehiculos')}

        if 'actualizado_por' in cols:
            op.drop_column('modelos_vehiculos', 'actualizado_por')
        if 'fecha_actualizacion' in cols:
            op.drop_column('modelos_vehiculos', 'fecha_actualizacion')
        if 'precio' in cols:
            op.drop_column('modelos_vehiculos', 'precio')
    except Exception:
        pass


