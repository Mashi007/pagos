
from datetime import date
Revision ID: 007_add_cargo_column_users
Revises: 006_update_user_roles_system
Create Date: 2025-10-17 20:20:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "007_add_cargo_column_users"
down_revision = "006_update_user_roles_system"
branch_labels = None
depends_on = None


def upgrade():
    # Verificar si la columna ya existe antes de agregarla
    connection = op.get_bind()

    # Verificar si la columna cargo existe
    result = connection.execute
        )
    )

    if not result.fetchone():
        # La columna no existe, agregarla
        op.add_column
        )
    else:


def downgrade():
    # Verificar si la columna existe antes de eliminarla
    connection = op.get_bind()

    result = connection.execute
        )
    )

    if result.fetchone():
        # La columna existe, eliminarla
    else:

"""