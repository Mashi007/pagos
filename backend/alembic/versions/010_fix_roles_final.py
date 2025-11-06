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
    
    if "users" not in inspector.get_table_names():
        print("⚠️ Tabla 'users' no existe, saltando migración")
        return
    
    columns = [col["name"] for col in inspector.get_columns("users")]

    if "is_admin" not in columns:
        # Agregar columna is_admin si no existe
        op.add_column(
            "users",
            sa.Column("is_admin", sa.Boolean(), nullable=False, server_default="false"),
        )

        try:
            if "rol" in columns:
                # Migrar datos de rol a is_admin si existe la columna rol
                op.execute(sa.text("UPDATE users SET is_admin = true WHERE rol = 'admin'"))
            else:
                # Si no existe rol, asumir que el primer usuario es admin
                op.execute(sa.text("UPDATE users SET is_admin = true WHERE id = (SELECT MIN(id) FROM users)"))
        except Exception as e:
            print(f"⚠️ No se pudo migrar datos de rol: {e}")

    # Verificar que is_admin esté configurado correctamente
    try:
        result = connection.execute(sa.text("SELECT COUNT(*) FROM users WHERE is_admin = true"))
        admin_count = result.scalar()

        if admin_count == 0:
            # Si no hay admins, hacer el primer usuario admin
            op.execute(sa.text("UPDATE users SET is_admin = true WHERE id = (SELECT MIN(id) FROM users)"))
    except Exception as e:
        print(f"⚠️ No se pudo verificar/configurar admins: {e}")


def downgrade() -> None:
    # Revertir: eliminar columna is_admin
    # Nota: Esta migración no revierte automáticamente los cambios
    # ya que puede haber dependencias. Se recomienda hacerlo manualmente si es necesario.
    pass
