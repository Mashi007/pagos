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
    
    # Drop the problematic unique index
    op.execute(text("DROP INDEX IF EXISTS ix_clientes_cedula"))

    # Create a non-unique index for performance
    indexes = [idx["name"] for idx in inspector.get_indexes("clientes")]
    if "idx_clientes_cedula_performance" not in indexes:
        op.execute(
            text("CREATE INDEX IF NOT EXISTS idx_clientes_cedula_performance ON clientes (cedula)")
        )


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
