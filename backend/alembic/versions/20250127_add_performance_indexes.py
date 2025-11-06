"""Agregar índices de performance para optimización de queries

Revision ID: 20250127_performance_indexes
Revises: 20251102_add_leida_notificaciones, 20250115_valor_activo, 20251030_usuario_autoriza, 20251030_eliminar_columnas_clientes, 20251030_modelos_precio
Create Date: 2025-01-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '20250127_performance_indexes'
down_revision = ('20251102_add_leida_notificaciones', '20250115_valor_activo', '20251030_usuario_autoriza', '20251030_del_cols_clientes', '20251030_modelos_precio')
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
    Agregar índices de performance en campos críticos.
    Esta migración es idempotente y segura - puede ejecutarse múltiples veces.
    """
    connection = op.get_bind()
    inspector = inspect(connection)
    
    # ============================================
    # ÍNDICE 1: pagos.fecha_registro
    # ============================================
    if _table_exists(inspector, 'pagos'):
        if _column_exists(inspector, 'pagos', 'fecha_registro'):
            index_name = 'ix_pagos_fecha_registro'
            if not _index_exists(inspector, 'pagos', index_name):
                try:
                    op.create_index(
                        index_name,
                        'pagos',
                        ['fecha_registro'],
                        unique=False
                    )
                    print(f"✅ Índice '{index_name}' creado en tabla 'pagos'")
                except Exception as e:
                    print(f"⚠️ Advertencia: No se pudo crear índice '{index_name}': {e}")
            else:
                print(f"ℹ️ Índice '{index_name}' ya existe, omitiendo...")
        else:
            print("ℹ️ Columna 'fecha_registro' no existe en tabla 'pagos', omitiendo índice...")
    else:
        print("ℹ️ Tabla 'pagos' no existe, omitiendo índice...")
    
    # ============================================
    # ÍNDICE 2: cuotas.fecha_vencimiento
    # ============================================
    if _table_exists(inspector, 'cuotas'):
        if _column_exists(inspector, 'cuotas', 'fecha_vencimiento'):
            index_name = 'ix_cuotas_fecha_vencimiento'
            if not _index_exists(inspector, 'cuotas', index_name):
                try:
                    op.create_index(
                        index_name,
                        'cuotas',
                        ['fecha_vencimiento'],
                        unique=False
                    )
                    print(f"✅ Índice '{index_name}' creado en tabla 'cuotas'")
                except Exception as e:
                    print(f"⚠️ Advertencia: No se pudo crear índice '{index_name}': {e}")
            else:
                print(f"ℹ️ Índice '{index_name}' ya existe, omitiendo...")
        else:
            print("ℹ️ Columna 'fecha_vencimiento' no existe en tabla 'cuotas', omitiendo índice...")
    else:
        print("ℹ️ Tabla 'cuotas' no existe, omitiendo índice...")
    
    # ============================================
    # ÍNDICE 3: prestamos.fecha_registro
    # ============================================
    if _table_exists(inspector, 'prestamos'):
        if _column_exists(inspector, 'prestamos', 'fecha_registro'):
            index_name = 'ix_prestamos_fecha_registro'
            if not _index_exists(inspector, 'prestamos', index_name):
                try:
                    op.create_index(
                        index_name,
                        'prestamos',
                        ['fecha_registro'],
                        unique=False
                    )
                    print(f"✅ Índice '{index_name}' creado en tabla 'prestamos'")
                except Exception as e:
                    print(f"⚠️ Advertencia: No se pudo crear índice '{index_name}': {e}")
            else:
                print(f"ℹ️ Índice '{index_name}' ya existe, omitiendo...")
        else:
            print("ℹ️ Columna 'fecha_registro' no existe en tabla 'prestamos', omitiendo índice...")
    else:
        print("ℹ️ Tabla 'prestamos' no existe, omitiendo índice...")
    
    # ============================================
    # ÍNDICE 4: prestamos_auditoria.fecha_cambio
    # ============================================
    if _table_exists(inspector, 'prestamos_auditoria'):
        if _column_exists(inspector, 'prestamos_auditoria', 'fecha_cambio'):
            index_name = 'ix_prestamos_auditoria_fecha_cambio'
            if not _index_exists(inspector, 'prestamos_auditoria', index_name):
                try:
                    op.create_index(
                        index_name,
                        'prestamos_auditoria',
                        ['fecha_cambio'],
                        unique=False
                    )
                    print(f"✅ Índice '{index_name}' creado en tabla 'prestamos_auditoria'")
                except Exception as e:
                    print(f"⚠️ Advertencia: No se pudo crear índice '{index_name}': {e}")
            else:
                print(f"ℹ️ Índice '{index_name}' ya existe, omitiendo...")
        else:
            print("ℹ️ Columna 'fecha_cambio' no existe en tabla 'prestamos_auditoria', omitiendo índice...")
    else:
        print("ℹ️ Tabla 'prestamos_auditoria' no existe, omitiendo índice...")
    
    print("\n✅ Migración de índices de performance completada")


def downgrade():
    """
    Eliminar índices de performance (rollback seguro).
    Verifica existencia antes de eliminar para evitar errores.
    """
    connection = op.get_bind()
    inspector = inspect(connection)
    
    # Eliminar índices si existen
    indices_to_drop = [
        ('pagos', 'ix_pagos_fecha_registro'),
        ('cuotas', 'ix_cuotas_fecha_vencimiento'),
        ('prestamos', 'ix_prestamos_fecha_registro'),
        ('prestamos_auditoria', 'ix_prestamos_auditoria_fecha_cambio'),
    ]
    
    for table_name, index_name in indices_to_drop:
        if _table_exists(inspector, table_name) and _index_exists(inspector, table_name, index_name):
            try:
                op.drop_index(index_name, table_name=table_name)
                print(f"✅ Índice '{index_name}' eliminado de tabla '{table_name}'")
            except Exception as e:
                print(f"⚠️ Advertencia: No se pudo eliminar índice '{index_name}': {e}")
        else:
            if not _table_exists(inspector, table_name):
                print(f"ℹ️ Tabla '{table_name}' no existe, omitiendo eliminación de índice...")
            else:
                print(f"ℹ️ Índice '{index_name}' no existe en tabla '{table_name}', omitiendo...")
    
    print("\n✅ Rollback de índices de performance completado")

