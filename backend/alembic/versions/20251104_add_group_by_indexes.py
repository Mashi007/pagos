"""Agregar índices funcionales para optimizar GROUP BY con EXTRACT

Revision ID: 20251104_group_by_indexes
Revises: 20251104_critical_indexes
Create Date: 2025-11-04 13:00:00.000000

"""
from alembic import op
from sqlalchemy import inspect, text

# revision identifiers, used by Alembic.
revision = '20251104_group_by_indexes'
down_revision = '20251104_critical_indexes'
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
    Agregar índices funcionales para optimizar GROUP BY con EXTRACT(YEAR, MONTH).
    Estas queries son usadas en:
    - /dashboard/evolucion-pagos (EXTRACT YEAR/MONTH FROM fecha_pago)
    - /dashboard/cobranzas-mensuales (EXTRACT YEAR/MONTH FROM fecha_vencimiento)
    - /dashboard/evolucion-morosidad (EXTRACT YEAR/MONTH FROM fecha_vencimiento)
    """
    connection = op.get_bind()
    inspector = inspect(connection)
    
    print("\n🚀 Iniciando migración de índices funcionales para GROUP BY...")
    
    # ============================================
    # ÍNDICES FUNCIONALES: PAGOS_STAGING
    # Para GROUP BY EXTRACT(YEAR/MONTH FROM fecha_pago)
    # ============================================
    if _table_exists(inspector, 'pagos_staging'):
        # Índice funcional para EXTRACT(YEAR FROM fecha_pago::timestamp)
        index_name = 'idx_pagos_staging_extract_year'
        if not _index_exists(inspector, 'pagos_staging', index_name):
            if _column_exists(inspector, 'pagos_staging', 'fecha_pago'):
                try:
                    connection.execute(text(
                        f"CREATE INDEX IF NOT EXISTS {index_name} "
                        f"ON pagos_staging USING btree (EXTRACT(YEAR FROM fecha_pago::timestamp)) "
                        f"WHERE fecha_pago IS NOT NULL AND fecha_pago != '' AND fecha_pago ~ '^\\d{{4}}-\\d{{2}}-\\d{{2}}'"
                    ))
                    print(f"✅ Índice funcional '{index_name}' creado para GROUP BY YEAR")
                except Exception as e:
                    print(f"⚠️ Advertencia: No se pudo crear índice '{index_name}': {e}")
            else:
                print("ℹ️ Columna 'fecha_pago' no existe en 'pagos_staging', omitiendo...")
        else:
            print(f"ℹ️ Índice '{index_name}' ya existe, omitiendo...")
        
        # Índice compuesto funcional para EXTRACT(YEAR, MONTH FROM fecha_pago::timestamp)
        index_name = 'idx_pagos_staging_extract_year_month'
        if not _index_exists(inspector, 'pagos_staging', index_name):
            if _column_exists(inspector, 'pagos_staging', 'fecha_pago'):
                try:
                    connection.execute(text(
                        f"CREATE INDEX IF NOT EXISTS {index_name} "
                        f"ON pagos_staging USING btree ("
                        f"  EXTRACT(YEAR FROM fecha_pago::timestamp), "
                        f"  EXTRACT(MONTH FROM fecha_pago::timestamp)"
                        f") "
                        f"WHERE fecha_pago IS NOT NULL AND fecha_pago != '' AND fecha_pago ~ '^\\d{{4}}-\\d{{2}}-\\d{{2}}'"
                    ))
                    print(f"✅ Índice compuesto funcional '{index_name}' creado para GROUP BY YEAR, MONTH")
                except Exception as e:
                    print(f"⚠️ Advertencia: No se pudo crear índice '{index_name}': {e}")
            else:
                print("ℹ️ Columna 'fecha_pago' no existe en 'pagos_staging', omitiendo...")
        else:
            print(f"ℹ️ Índice '{index_name}' ya existe, omitiendo...")
    else:
        print("ℹ️ Tabla 'pagos_staging' no existe, omitiendo índices...")
    
    # ============================================
    # ÍNDICES FUNCIONALES: CUOTAS
    # Para GROUP BY EXTRACT(YEAR/MONTH FROM fecha_vencimiento)
    # ============================================
    if _table_exists(inspector, 'cuotas'):
        # Índice compuesto funcional para EXTRACT(YEAR, MONTH FROM fecha_vencimiento)
        index_name = 'idx_cuotas_extract_year_month'
        if not _index_exists(inspector, 'cuotas', index_name):
            if _column_exists(inspector, 'cuotas', 'fecha_vencimiento'):
                try:
                    connection.execute(text(
                        f"CREATE INDEX IF NOT EXISTS {index_name} "
                        f"ON cuotas USING btree ("
                        f"  EXTRACT(YEAR FROM fecha_vencimiento), "
                        f"  EXTRACT(MONTH FROM fecha_vencimiento)"
                        f") "
                        f"WHERE fecha_vencimiento IS NOT NULL"
                    ))
                    print(f"✅ Índice compuesto funcional '{index_name}' creado para GROUP BY YEAR, MONTH")
                except Exception as e:
                    print(f"⚠️ Advertencia: No se pudo crear índice '{index_name}': {e}")
            else:
                print("ℹ️ Columna 'fecha_vencimiento' no existe en 'cuotas', omitiendo...")
        else:
            print(f"ℹ️ Índice '{index_name}' ya existe, omitiendo...")
    else:
        print("ℹ️ Tabla 'cuotas' no existe, omitiendo índices...")
    
    # Ejecutar ANALYZE para actualizar estadísticas
    try:
        print("\n📊 Actualizando estadísticas de tablas...")
        tables_to_analyze = ['pagos_staging', 'cuotas']
        for table in tables_to_analyze:
            if _table_exists(inspector, table):
                try:
                    connection.execute(text(f"ANALYZE {table}"))
                    print(f"✅ ANALYZE ejecutado en '{table}'")
                except Exception as e:
                    print(f"⚠️ No se pudo ejecutar ANALYZE en '{table}': {e}")
    except Exception as e:
        print(f"⚠️ Advertencia al ejecutar ANALYZE: {e}")
    
    print("\n✅ Migración de índices funcionales para GROUP BY completada")
    print("📈 Impacto esperado: Reducción de tiempos de GROUP BY de 17-31s a <2s")


def downgrade():
    """
    Eliminar índices funcionales para GROUP BY (rollback seguro).
    """
    connection = op.get_bind()
    inspector = inspect(connection)
    
    print("\n🔄 Iniciando rollback de índices funcionales para GROUP BY...")
    
    indices_to_drop = [
        ('pagos_staging', 'idx_pagos_staging_extract_year'),
        ('pagos_staging', 'idx_pagos_staging_extract_year_month'),
        ('cuotas', 'idx_cuotas_extract_year_month'),
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
                print(f"ℹ️ Tabla '{table_name}' no existe, omitiendo eliminación...")
            else:
                print(f"ℹ️ Índice '{index_name}' no existe en '{table_name}', omitiendo...")
    
    print("\n✅ Rollback de índices funcionales para GROUP BY completado")

