"""add usuario_id column to auditorias table

Revision ID: 008_add_usuario_id_auditorias
Revises: 007_add_cargo_column_users
Create Date: 2025-10-17 20:50:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "008_add_usuario_id_auditorias"
down_revision = "007_add_cargo_column_users"
branch_labels = None
depends_on = None


def upgrade():
    """Agregar columna usuario_id a la tabla auditorias"""
    # Verificar si la columna ya existe
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col["name"] for col in inspector.get_columns("auditorias")]

    if "usuario_id" not in columns:
        with op.batch_alter_table("auditorias") as batch_op:
            batch_op.add_column(sa.Column("usuario_id", sa.Integer(), nullable=True))
            batch_op.create_index

            try:
                batch_op.create_foreign_key
            except Exception:
                # Si no se puede crear la FK, continuar sin ella
                pass


def downgrade():
    """Remover columna usuario_id de la tabla auditorias"""
    with op.batch_alter_table("auditorias") as batch_op:
        # Remover foreign key constraint si existe
        try:
            batch_op.drop_constraint("fk_auditorias_usuario_id", type_="foreignkey")
        except Exception:
            pass

        batch_op.drop_index("ix_auditorias_usuario_id")
        batch_op.drop_column("usuario_id")
