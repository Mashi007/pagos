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

    # Paso 1: Agregar columna is_admin
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default="false"),
    )


    # Paso 3: Eliminar columna rol (opcional, comentado por seguridad)

    # Paso 4: Eliminar enum userrole (opcional, comentado por seguridad)
    # op.execute("DROP TYPE IF EXISTS userrole")


def downgrade() -> None:
    # Revertir: eliminar columna is_admin
    op.drop_column("users", "is_admin")
