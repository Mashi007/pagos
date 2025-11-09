"""EMERGENCY: Force remove unique index ix_clientes_cedula

Revision ID: 016_emergency_remove_unique_index_cedula
Revises: 015_remove_unique_constraint_cedula_fixed
Create Date: 2025-01-21 02:15:00.000000

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "016_emergency_rm_unique_idx"
down_revision = "015_remove_unique_cedula_fix"
branch_labels = None
depends_on = None


def upgrade():
    """EMERGENCY: Force remove the unique index ix_clientes_cedula"""
    from sqlalchemy import text
    connection = op.get_bind()

    # Verificar existencia usando SQL directo para evitar problemas de transacción
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

    # Drop the problematic unique index
    try:
        connection.execute(text("DROP INDEX IF EXISTS ix_clientes_cedula"))
        print("✅ Índice 'ix_clientes_cedula' eliminado (si existía)")
    except Exception as e:
        print(f"⚠️ No se pudo eliminar índice: {e}")

    # Create a non-unique index for performance usando SQL directo
    try:
        # Verificar si el índice ya existe usando SQL directo
        result = connection.execute(text("""
            SELECT EXISTS (
                SELECT FROM pg_indexes
                WHERE schemaname = 'public'
                AND tablename = 'clientes'
                AND indexname = 'idx_clientes_cedula_performance'
            )
        """))
        index_exists = result.scalar()

        if not index_exists:
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_clientes_cedula_performance ON clientes (cedula)"))
            print("✅ Índice 'idx_clientes_cedula_performance' creado")
        else:
            print("ℹ️ Índice 'idx_clientes_cedula_performance' ya existe, omitiendo...")
    except Exception as e:
        print(f"⚠️ No se pudo crear índice: {e}")


def downgrade():
    """Restore the unique index"""
    import sqlalchemy as sa
    from sqlalchemy import text
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    if "clientes" not in inspector.get_table_names():
        return

    columns = [col["name"] for col in inspector.get_columns("clientes")]
    if "cedula" not in columns:
        return

    # Drop the performance index
    op.execute(text("DROP INDEX IF EXISTS idx_clientes_cedula_performance"))

    # Restore the unique index
    try:
        op.execute(text("CREATE UNIQUE INDEX ix_clientes_cedula ON clientes (cedula)"))
    except Exception as e:
        print(f"⚠️ No se pudo crear índice único: {e}")
