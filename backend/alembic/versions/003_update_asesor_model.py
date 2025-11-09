"""Update asesor model - make apellido and email nullable

Revision ID: 003_update_asesor_model
Revises: 003_create_auditoria_table
Create Date: 2025-10-15 15:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "003_update_asesor_model"
down_revision = "003_create_auditoria_table"
branch_labels = None
depends_on = None


def upgrade():
    """Update asesor model to make apellido and email nullable"""
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    if "asesores" not in inspector.get_table_names():
        print("⚠️ Tabla 'asesores' no existe, saltando migración")
        return

    columns = [col["name"] for col in inspector.get_columns("asesores")]

    # Make apellido nullable
    if "apellido" in columns:
        try:
            op.alter_column(
                "asesores", "apellido", existing_type=sa.VARCHAR(255), nullable=True
            )
        except Exception as e:
            print(f"⚠️ No se pudo modificar columna 'apellido': {e}")

    # Make email nullable
    if "email" in columns:
        try:
            op.alter_column("asesores", "email", existing_type=sa.VARCHAR(255), nullable=True)
        except Exception as e:
            print(f"⚠️ No se pudo modificar columna 'email': {e}")


def downgrade():
    """Revert asesor model changes"""
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    if "asesores" not in inspector.get_table_names():
        return

    columns = [col["name"] for col in inspector.get_columns("asesores")]

    # Make apellido not nullable
    if "apellido" in columns:
        try:
            op.alter_column(
                "asesores", "apellido", existing_type=sa.VARCHAR(255), nullable=False
            )
        except Exception as e:
            print(f"⚠️ No se pudo modificar columna 'apellido': {e}")

    # Make email not nullable
    if "email" in columns:
        try:
            op.alter_column("asesores", "email", existing_type=sa.VARCHAR(255), nullable=False)
        except Exception as e:
            print(f"⚠️ No se pudo modificar columna 'email': {e}")
