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
    from sqlalchemy import text
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    if "clientes" not in inspector.get_table_names():
        print("⚠️ Tabla 'clientes' no existe, saltando migración")
        return
    
    columns = [col["name"] for col in inspector.get_columns("clientes")]
    if "cedula" not in columns:
        print("⚠️ Columna 'cedula' no existe en tabla 'clientes', saltando migración")
        return
    
    # Verificar si el constraint existe antes de eliminarlo
    try:
        constraints = [c["name"] for c in inspector.get_unique_constraints("clientes")]
        if "clientes_cedula_key" in constraints:
            # Usar SQL directo con IF EXISTS para evitar abortar la transacción
            op.execute(text("ALTER TABLE clientes DROP CONSTRAINT IF EXISTS clientes_cedula_key"))
            print("✅ Constraint único 'clientes_cedula_key' eliminado")
        else:
            print("⚠️ Constraint único 'clientes_cedula_key' no existe, omitiendo...")
    except Exception as e:
        # Si falla la verificación, intentar con SQL directo de todas formas
        try:
            op.execute(text("ALTER TABLE clientes DROP CONSTRAINT IF EXISTS clientes_cedula_key"))
            print("✅ Constraint único 'clientes_cedula_key' eliminado (usando SQL directo)")
        except Exception as e2:
            print(f"⚠️ No se pudo eliminar constraint único: {e2}")

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
