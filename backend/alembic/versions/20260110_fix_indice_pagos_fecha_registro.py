"""Fix índice ix_pagos_fecha_registro - Auditoría detectó que falta

Revision ID: 20260110_fix_pagos_fecha_registro_index
Revises: 20250127_performance_indexes
Create Date: 2026-01-10 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

# revision identifiers, used by Alembic.
revision = '20260110_fix_pagos_fecha_registro_index'
down_revision = '20250127_performance_indexes'
branch_labels = None
depends_on = None


def _index_exists(inspector, table_name: str, index_name: str) -> bool:
    """Verifica si un índice existe en una tabla"""
    try:
        indexes = inspector.get_indexes(table_name)
        return any(idx['name'] == index_name for idx in indexes)
    except Exception:
        return False


def _table_exists(inspector, table_name: str) -> bool:
    """Verifica si una tabla existe"""
    try:
        return table_name in inspector.get_table_names()
    except Exception:
        return False


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    """Verifica si una columna existe en una tabla"""
    try:
        columns = inspector.get_columns(table_name)
        return any(col['name'] == column_name for col in columns)
    except Exception:
        return False


def upgrade():
    """
    Crear índice ix_pagos_fecha_registro si no existe.
    Este índice fue detectado como faltante en la auditoría integral del endpoint /pagos.
    """
    connection = op.get_bind()
    inspector = inspect(connection)

    index_name = 'ix_pagos_fecha_registro'
    table_name = 'pagos'
    column_name = 'fecha_registro'

    if not _table_exists(inspector, table_name):
        print(f"⚠️ Tabla '{table_name}' no existe, omitiendo creación de índice...")
        return

    if not _column_exists(inspector, table_name, column_name):
        print(f"⚠️ Columna '{column_name}' no existe en tabla '{table_name}', omitiendo índice...")
        return

    if _index_exists(inspector, table_name, index_name):
        print(f"ℹ️ Índice '{index_name}' ya existe en tabla '{table_name}', omitiendo...")
        return

    try:
        # Usar SQL directo para mayor compatibilidad
        connection.execute(text(
            f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({column_name})"
        ))
        connection.commit()
        print(f"✅ Índice '{index_name}' creado exitosamente en tabla '{table_name}'")
    except Exception as e:
        # Si falla con IF NOT EXISTS, intentar sin él
        try:
            op.create_index(
                index_name,
                table_name,
                [column_name],
                unique=False
            )
            print(f"✅ Índice '{index_name}' creado exitosamente en tabla '{table_name}' (método alternativo)")
        except Exception as e2:
            print(f"❌ Error creando índice '{index_name}': {e2}")
            raise


def downgrade():
    """
    Eliminar índice ix_pagos_fecha_registro si existe.
    """
    connection = op.get_bind()
    inspector = inspect(connection)

    index_name = 'ix_pagos_fecha_registro'
    table_name = 'pagos'

    if not _table_exists(inspector, table_name):
        print(f"ℹ️ Tabla '{table_name}' no existe, omitiendo eliminación de índice...")
        return

    if not _index_exists(inspector, table_name, index_name):
        print(f"ℹ️ Índice '{index_name}' no existe en tabla '{table_name}', omitiendo...")
        return

    try:
        op.drop_index(index_name, table_name=table_name)
        print(f"✅ Índice '{index_name}' eliminado de tabla '{table_name}'")
    except Exception as e:
        print(f"⚠️ Advertencia: No se pudo eliminar índice '{index_name}': {e}")
