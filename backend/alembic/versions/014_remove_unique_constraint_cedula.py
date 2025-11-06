"""remove unique constraint from cedula

Revision ID: 014_remove_unique_constraint_cedula
Revises: 013_create_pagos_table
Create Date: 2025-01-21 01:25:00.000000

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "014_remove_unique_cedula"
down_revision = "013_create_pagos_table"
branch_labels = None
depends_on = None


def upgrade():
    """Remove unique constraint from cedula column in clientes table"""
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
    
    # Drop the unique constraint on cedula column
    try:
        op.drop_constraint("clientes_cedula_key", "clientes", type_="unique")
    except Exception as e:
        print(f"⚠️ No se pudo eliminar constraint único: {e}")

    # Keep the index for performance
    # op.create_index('ix_clientes_cedula', 'clientes', ['cedula'])


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
    
    # Restore the unique constraint
    try:
        op.create_unique_constraint("clientes_cedula_key", "clientes", ["cedula"])
    except Exception as e:
        print(f"⚠️ No se pudo crear constraint único: {e}")
