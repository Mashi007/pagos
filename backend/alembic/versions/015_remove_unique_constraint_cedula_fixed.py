"""remove unique constraint from cedula - CORREGIDA

Revision ID: 015_remove_unique_constraint_cedula_fixed
Revises: 014_remove_unique_constraint_cedula
Create Date: 2025-01-21 02:05:00.000000

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "015_remove_unique_cedula_fix"
down_revision = "014_remove_unique_cedula"
branch_labels = None
depends_on = None


def upgrade():
    """Remove ALL unique constraints from cedula column in clientes table"""
    import sqlalchemy as sa
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    if "clientes" not in inspector.get_table_names():
        print("⚠️ Tabla 'clientes' no existe, saltando migración")
        return
    
    columns = [col["name"] for col in inspector.get_columns("clientes")]
    if "cedula" not in columns:
        print("⚠️ Columna 'cedula' no existe en tabla 'clientes', saltando migración")
        return
    
    try:
        op.drop_constraint("clientes_cedula_key", "clientes", type_="unique")
    except Exception:
        pass  # Constraint might not exist

    try:
        op.drop_constraint("ix_clientes_cedula", "clientes", type_="unique")
    except Exception:
        pass  # Constraint might not exist

    try:
        op.drop_index("ix_clientes_cedula", "clientes")
    except Exception:
        pass  # Index might not exist

    # Create a non-unique index for performance
    indexes = [idx["name"] for idx in inspector.get_indexes("clientes")]
    if "ix_clientes_cedula_non_unique" not in indexes:
        op.create_index("ix_clientes_cedula_non_unique", "clientes", ["cedula"], unique=False)


def downgrade():
    """Restore unique constraint on cedula column in clientes table"""
    import sqlalchemy as sa
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    if "clientes" not in inspector.get_table_names():
        return
    
    columns = [col["name"] for col in inspector.get_columns("clientes")]
    if "cedula" not in columns:
        return
    
    # Drop the non-unique index
    try:
        op.drop_index("ix_clientes_cedula_non_unique", "clientes")
    except Exception:
        pass

    # Restore the unique constraint
    try:
        op.create_unique_constraint("clientes_cedula_key", "clientes", ["cedula"])
    except Exception as e:
        print(f"⚠️ No se pudo crear constraint único: {e}")
