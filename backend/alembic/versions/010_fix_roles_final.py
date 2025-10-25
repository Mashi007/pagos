"""Corregir migraciones anteriores y aplicar simplificación de roles

Revision ID: 010_fix_roles_final
Revises: 009_simplify_roles_to_boolean
Create Date: 2024-10-18 13:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "010_fix_roles_final"
down_revision: Union[str, None] = "009_simplify_roles_to_boolean"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # Verificar si la columna is_admin ya existe
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    if "is_admin" not in columns:
        # Agregar columna is_admin si no existe
        op.add_column
            sa.Column("is_admin", sa.Boolean(), nullable=False, server_default="false"),

        if "rol" in columns:
        else:
            # Si no existe rol, asumir que el primer usuario es admin

    # Verificar que is_admin esté configurado correctamente
    result = connection.execute
    admin_count = result.scalar()

    if admin_count == 0:
        # Si no hay admins, hacer el primer usuario admin
        op.execute


def downgrade() -> None:

    # Revertir: eliminar columna is_admin
