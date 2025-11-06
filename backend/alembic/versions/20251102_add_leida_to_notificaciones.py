"""agregar columna leida a notificaciones

Revision ID: 20251102_add_leida
Revises: 20251030_add_cols_notificaciones
Create Date: 2025-11-02 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "20251102_add_leida"
down_revision = "20251030_add_cols_notificaciones"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    inspector = inspect(connection)

    # Si la tabla no existe, no hacemos nada para evitar fallos en entornos parciales
    if "notificaciones" not in inspector.get_table_names():
        return

    columns = [c["name"] for c in inspector.get_columns("notificaciones")]

    if "leida" not in columns:
        op.add_column(
            "notificaciones",
            sa.Column("leida", sa.Boolean(), nullable=False, server_default="false"),
        )


def downgrade():
    connection = op.get_bind()
    inspector = inspect(connection)

    if "notificaciones" not in inspector.get_table_names():
        return

    columns = [c["name"] for c in inspector.get_columns("notificaciones")]
    if "leida" in columns:
        op.drop_column("notificaciones", "leida")


