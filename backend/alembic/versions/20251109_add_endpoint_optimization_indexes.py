"""Agregar índices críticos para optimización de endpoints del dashboard

Revision ID: 20251109_endpoint_optimization_indexes
Revises: 20251108_add_updated_at
Create Date: 2025-11-09 17:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

# revision identifiers, used by Alembic.
revision = '20251109_endpoint_optimization_indexes'
down_revision = '20251108_add_updated_at'
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
    Agregar índices críticos para optimizar endpoints del dashboard.

    PRIORIDAD ALTA:
    1. idx_prestamos_estado_fecha_aprobacion - Optimiza kpis-principales
    2. idx_prestamos_total_financiamiento - Optimiza financiamiento-por-rangos
    3. idx_cuotas_dias_morosidad - Optimiza composicion-morosidad
    4. idx_cuotas_fecha_vencimiento - Optimiza clientes-atrasados
    """
    connection = op.get_bind()
    inspector = inspect(connection)

    print("\n🚀 Iniciando migración de índices para optimización de endpoints...")

    # ============================================
    # ÍNDICES CRÍTICOS: PRESTAMOS
    # ============================================
    if _table_exists(inspector, 'prestamos'):
        # 1. Índice compuesto: estado + fecha_aprobacion
        # Optimiza: /dashboard/kpis-principales
        index_name = 'idx_prestamos_estado_fecha_aprobacion'
        if not _index_exists(inspector, 'prestamos', index_name):
            if (_column_exists(inspector, 'prestamos', 'estado') and
                _column_exists(inspector, 'prestamos', 'fecha_aprobacion')):
                try:
                    op.create_index(
                        index_name,
                        'prestamos',
                        ['estado', 'fecha_aprobacion'],
                        unique=False
                    )
                    print(f"✅ Índice compuesto '{index_name}' creado en tabla 'prestamos'")
                except Exception as e:
                    print(f"⚠️ Advertencia: No se pudo crear índice '{index_name}': {e}")
            else:
                print("ℹ️ Columnas requeridas no existen en 'prestamos', omitiendo...")
        else:
            print(f"ℹ️ Índice '{index_name}' ya existe, omitiendo...")

        # 2. Índice en total_financiamiento (parcial para APROBADO)
        # Optimiza: /dashboard/financiamiento-por-rangos
        index_name = 'idx_prestamos_total_financiamiento'
        if not _index_exists(inspector, 'prestamos', index_name):
            if _column_exists(inspector, 'prestamos', 'total_financiamiento'):
                try:
                    # Índice parcial - usar SQL directo para WHERE clause
                    connection.execute(text(
                        f"CREATE INDEX IF NOT EXISTS {index_name} "
                        f"ON prestamos (total_financiamiento) "
                        f"WHERE estado = 'APROBADO' AND total_financiamiento > 0"
                    ))
                    print(f"✅ Índice parcial '{index_name}' creado en tabla 'prestamos'")
                except Exception as e:
                    print(f"⚠️ Advertencia: No se pudo crear índice '{index_name}': {e}")
            else:
                print("ℹ️ Columna 'total_financiamiento' no existe en 'prestamos', omitiendo...")
        else:
            print(f"ℹ️ Índice '{index_name}' ya existe, omitiendo...")

        # 3. Índice funcional para date_trunc('month', fecha_aprobacion)
        # Optimiza: /dashboard/financiamiento-tendencia-mensual
        index_name = 'idx_prestamos_fecha_aprobacion_month'
        if not _index_exists(inspector, 'prestamos', index_name):
            if _column_exists(inspector, 'prestamos', 'fecha_aprobacion'):
                try:
                    connection.execute(text(
                        f"CREATE INDEX IF NOT EXISTS {index_name} "
                        f"ON prestamos USING btree (date_trunc('month', fecha_aprobacion)) "
                        f"WHERE estado = 'APROBADO' AND fecha_aprobacion IS NOT NULL"
                    ))
                    print(f"✅ Índice funcional '{index_name}' creado para GROUP BY mensual")
                except Exception as e:
                    print(f"⚠️ Advertencia: No se pudo crear índice '{index_name}': {e}")
            else:
                print("ℹ️ Columna 'fecha_aprobacion' no existe en 'prestamos', omitiendo...")
        else:
            print(f"ℹ️ Índice '{index_name}' ya existe, omitiendo...")
    else:
        print("ℹ️ Tabla 'prestamos' no existe, omitiendo índices...")

    # ============================================
    # ÍNDICES CRÍTICOS: CUOTAS
    # ============================================
    if _table_exists(inspector, 'cuotas'):
        # 4. Índice en dias_morosidad (parcial para > 0)
        # Optimiza: /dashboard/composicion-morosidad
        index_name = 'idx_cuotas_dias_morosidad'
        if not _index_exists(inspector, 'cuotas', index_name):
            if _column_exists(inspector, 'cuotas', 'dias_morosidad'):
                try:
                    connection.execute(text(
                        f"CREATE INDEX IF NOT EXISTS {index_name} "
                        f"ON cuotas (dias_morosidad) "
                        f"WHERE dias_morosidad > 0"
                    ))
                    print(f"✅ Índice parcial '{index_name}' creado en tabla 'cuotas'")
                except Exception as e:
                    print(f"⚠️ Advertencia: No se pudo crear índice '{index_name}': {e}")
            else:
                print("ℹ️ Columna 'dias_morosidad' no existe en 'cuotas', omitiendo...")
        else:
            print(f"ℹ️ Índice '{index_name}' ya existe, omitiendo...")

        # 5. Índice en monto_morosidad (parcial para > 0)
        # Optimiza: /dashboard/composicion-morosidad
        index_name = 'idx_cuotas_monto_morosidad'
        if not _index_exists(inspector, 'cuotas', index_name):
            if _column_exists(inspector, 'cuotas', 'monto_morosidad'):
                try:
                    connection.execute(text(
                        f"CREATE INDEX IF NOT EXISTS {index_name} "
                        f"ON cuotas (monto_morosidad) "
                        f"WHERE monto_morosidad > 0"
                    ))
                    print(f"✅ Índice parcial '{index_name}' creado en tabla 'cuotas'")
                except Exception as e:
                    print(f"⚠️ Advertencia: No se pudo crear índice '{index_name}': {e}")
            else:
                print("ℹ️ Columna 'monto_morosidad' no existe en 'cuotas', omitiendo...")
        else:
            print(f"ℹ️ Índice '{index_name}' ya existe, omitiendo...")

        # 6. Índice compuesto: fecha_vencimiento + estado + total_pagado
        # Optimiza: /cobranzas/clientes-atrasados
        index_name = 'idx_cuotas_vencimiento_estado_pago'
        if not _index_exists(inspector, 'cuotas', index_name):
            if (_column_exists(inspector, 'cuotas', 'fecha_vencimiento') and
                _column_exists(inspector, 'cuotas', 'estado') and
                _column_exists(inspector, 'cuotas', 'total_pagado')):
                try:
                    connection.execute(text(
                        f"CREATE INDEX IF NOT EXISTS {index_name} "
                        f"ON cuotas (fecha_vencimiento, estado, total_pagado) "
                        f"WHERE estado != 'PAGADO'"
                    ))
                    print(f"✅ Índice compuesto parcial '{index_name}' creado en tabla 'cuotas'")
                except Exception as e:
                    print(f"⚠️ Advertencia: No se pudo crear índice '{index_name}': {e}")
            else:
                print("ℹ️ Columnas requeridas no existen en 'cuotas', omitiendo...")
        else:
            print(f"ℹ️ Índice '{index_name}' ya existe, omitiendo...")
    else:
        print("ℹ️ Tabla 'cuotas' no existe, omitiendo índices...")

    # Ejecutar ANALYZE para actualizar estadísticas
    try:
        print("\n📊 Actualizando estadísticas de tablas...")
        tables_to_analyze = ['prestamos', 'cuotas']
        for table in tables_to_analyze:
            if _table_exists(inspector, table):
                try:
                    connection.execute(text(f"ANALYZE {table}"))
                    print(f"✅ ANALYZE ejecutado en '{table}'")
                except Exception as e:
                    print(f"⚠️ No se pudo ejecutar ANALYZE en '{table}': {e}")
    except Exception as e:
        print(f"⚠️ Advertencia al ejecutar ANALYZE: {e}")

    print("\n✅ Migración de índices para optimización de endpoints completada")
    print("📈 Impacto esperado:")
    print("   - kpis-principales: Reducción de 2-5s a <1s")
    print("   - financiamiento-por-rangos: Reducción de 1-3s a <500ms")
    print("   - composicion-morosidad: Reducción de 1-2s a <500ms")
    print("   - clientes-atrasados: Reducción de 500-1000ms a <300ms")


def downgrade():
    """
    Eliminar índices de optimización de endpoints (rollback seguro).
    """
    connection = op.get_bind()
    inspector = inspect(connection)

    print("\n🔄 Iniciando rollback de índices de optimización de endpoints...")

    indices_to_drop = [
        ('prestamos', 'idx_prestamos_estado_fecha_aprobacion'),
        ('prestamos', 'idx_prestamos_total_financiamiento'),
        ('prestamos', 'idx_prestamos_fecha_aprobacion_month'),
        ('cuotas', 'idx_cuotas_dias_morosidad'),
        ('cuotas', 'idx_cuotas_monto_morosidad'),
        ('cuotas', 'idx_cuotas_vencimiento_estado_pago'),
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

    print("\n✅ Rollback de índices de optimización de endpoints completado")
