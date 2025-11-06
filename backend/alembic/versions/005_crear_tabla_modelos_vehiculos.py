"""crear tabla modelos vehiculos

Revision ID: 005
Revises: 004_add_total_financiamiento
Create Date: 2025-10-15 01:55:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "005"
down_revision = "004_add_total_financiamiento"
branch_labels = None
depends_on = None


def upgrade():
    # Crear tabla modelos_vehiculos
    op.create_table(
        "modelos_vehiculos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("marca", sa.String(50), nullable=False),
        sa.Column("modelo", sa.String(100), nullable=False),
        sa.Column("nombre_completo", sa.String(150), nullable=False),
        sa.Column("categoria", sa.String(50), nullable=True),  # Sedán, SUV, Hatchback, etc.
        sa.Column("precio_base", sa.Numeric(12, 2), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("especificaciones", sa.JSON(), nullable=True),  # Motor, transmisión, etc.
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nombre_completo"),
    )

    # Crear índices
    op.create_index("ix_modelos_vehiculos_marca", "modelos_vehiculos", ["marca"])
    op.create_index("ix_modelos_vehiculos_modelo", "modelos_vehiculos", ["modelo"])
    op.create_index("ix_modelos_vehiculos_nombre_completo", "modelos_vehiculos", ["nombre_completo"])
    op.create_index("ix_modelos_vehiculos_activo", "modelos_vehiculos", ["activo"])

    # Nota: Los datos iniciales de modelos de vehículos pueden ser insertados
    # manualmente o a través de un script separado si es necesario.


def downgrade():
    # Eliminar índices
    op.drop_index("ix_modelos_vehiculos_activo", table_name="modelos_vehiculos")
    op.drop_index("ix_modelos_vehiculos_nombre_completo", table_name="modelos_vehiculos")
    op.drop_index("ix_modelos_vehiculos_modelo", table_name="modelos_vehiculos")
    op.drop_index("ix_modelos_vehiculos_marca", table_name="modelos_vehiculos")

    # Eliminar tabla
    op.drop_table("modelos_vehiculos")
