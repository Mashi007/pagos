"""agregar columnas canal y asunto a notificaciones

Revision ID: 20251030_add_cols_notificaciones
Revises: 20251030_actualizar_catalogos
Create Date: 2025-10-30 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "20251030_add_cols_notificaciones"
down_revision = "20251030_actualizar_catalogos"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    inspector = inspect(connection)

    # Si la tabla no existe, no hacemos nada para evitar fallos en entornos parciales
    if "notificaciones" not in inspector.get_table_names():
        return

    columns = [c["name"] for c in inspector.get_columns("notificaciones")]

    if "canal" not in columns:
        op.add_column(
            "notificaciones",
            sa.Column("canal", sa.String(length=20), nullable=True),
        )

    if "asunto" not in columns:
        op.add_column(
            "notificaciones",
            sa.Column("asunto", sa.String(length=255), nullable=True),
        )

    # Crear índices si ayudan a consultas por canal Y la columna existe
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("notificaciones")}
    if "ix_notificaciones_canal" not in existing_indexes and "canal" in columns:
        op.create_index("ix_notificaciones_canal", "notificaciones", ["canal"])


def downgrade():
    connection = op.get_bind()
    inspector = inspect(connection)

    if "notificaciones" not in inspector.get_table_names():
        return

    # Eliminar índice si existe
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("notificaciones")}
    if "ix_notificaciones_canal" in existing_indexes:
        op.drop_index("ix_notificaciones_canal", table_name="notificaciones")

    columns = [c["name"] for c in inspector.get_columns("notificaciones")]
    if "asunto" in columns:
        op.drop_column("notificaciones", "asunto")
    if "canal" in columns:
        op.drop_column("notificaciones", "canal")


