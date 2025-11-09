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
    from sqlalchemy import text

    connection = op.get_bind()

    # Verificar existencia de tabla usando SQL directo para evitar problemas de transacción
    try:
        result = connection.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'clientes'
            )
        """))
        table_exists = result.scalar()

        if not table_exists:
            print("⚠️ Tabla 'clientes' no existe, saltando migración")
            return

        # Verificar existencia de columna usando SQL directo
        result = connection.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = 'clientes'
                AND column_name = 'cedula'
            )
        """))
        column_exists = result.scalar()

        if not column_exists:
            print("⚠️ Columna 'cedula' no existe en tabla 'clientes', saltando migración")
            return
    except Exception as e:
        print(f"⚠️ Error verificando tabla/columna: {e}")
        # Continuar de todas formas, usar SQL directo con IF EXISTS

    # Eliminar constraints usando SQL directo con IF EXISTS
    try:
        connection.execute(text("ALTER TABLE clientes DROP CONSTRAINT IF EXISTS clientes_cedula_key"))
        print("✅ Constraint 'clientes_cedula_key' eliminado (si existía)")
    except Exception as e:
        print(f"⚠️ No se pudo eliminar constraint 'clientes_cedula_key': {e}")

    try:
        connection.execute(text("ALTER TABLE clientes DROP CONSTRAINT IF EXISTS ix_clientes_cedula"))
        print("✅ Constraint 'ix_clientes_cedula' eliminado (si existía)")
    except Exception as e:
        print(f"⚠️ No se pudo eliminar constraint 'ix_clientes_cedula': {e}")

    # Eliminar índice usando SQL directo con IF EXISTS
    try:
        connection.execute(text("DROP INDEX IF EXISTS ix_clientes_cedula"))
        print("✅ Índice 'ix_clientes_cedula' eliminado (si existía)")
    except Exception as e:
        print(f"⚠️ No se pudo eliminar índice 'ix_clientes_cedula': {e}")

    # Crear índice no único usando SQL directo con IF NOT EXISTS
    try:
        # Verificar si el índice ya existe usando SQL directo
        result = connection.execute(text("""
            SELECT EXISTS (
                SELECT FROM pg_indexes
                WHERE schemaname = 'public'
                AND tablename = 'clientes'
                AND indexname = 'ix_clientes_cedula_non_unique'
            )
        """))
        index_exists = result.scalar()

        if not index_exists:
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_clientes_cedula_non_unique ON clientes(cedula)"))
            print("✅ Índice no único 'ix_clientes_cedula_non_unique' creado")
        else:
            print("ℹ️ Índice 'ix_clientes_cedula_non_unique' ya existe, omitiendo...")
    except Exception as e:
        print(f"⚠️ No se pudo crear índice no único: {e}")


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
