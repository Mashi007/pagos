"""Simplificar roles: cambiar rol enum a is_admin boolean

Revision ID: 009_simplify_roles_to_boolean
Revises: 008_add_usuario_id_auditorias
Create Date: 2024-10-18 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "009_simplify_roles_to_boolean"
down_revision: Union[str, None] = "008_add_usuario_id_auditorias"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    if "users" not in inspector.get_table_names():
        print("⚠️ Tabla 'users' no existe, saltando migración")
        return

    columns = [col["name"] for col in inspector.get_columns("users")]

    # Paso 1: Agregar columna is_admin si no existe
    if "is_admin" not in columns:
        op.add_column(
            "users",
            sa.Column("is_admin", sa.Boolean(), nullable=False, server_default="false"),
        )
    else:
        print("⚠️ Columna 'is_admin' ya existe en tabla 'users'")


    # Paso 3: Eliminar columna rol (opcional, comentado por seguridad)

    # Paso 4: Eliminar enum userrole (opcional, comentado por seguridad)
    # op.execute("DROP TYPE IF EXISTS userrole")


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    if "users" not in inspector.get_table_names():
        return

    columns = [col["name"] for col in inspector.get_columns("users")]

    # Revertir: eliminar columna is_admin si existe
    if "is_admin" in columns:
        op.drop_column("users", "is_admin")
