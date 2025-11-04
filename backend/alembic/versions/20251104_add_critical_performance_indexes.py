"""Agregar índices críticos de performance para resolver timeouts

Revision ID: 20251104_critical_indexes
Revises: 20251102_add_leida_notificaciones
Create Date: 2025-11-04 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

# revision identifiers, used by Alembic.
revision = '20251104_critical_indexes'
down_revision = '20251102_add_leida_notificaciones'
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
    Agregar índices críticos de performance para resolver timeouts de 57+ segundos.
    
    NOTA IMPORTANTE: CREATE INDEX CONCURRENTLY no puede ejecutarse dentro de transacciones.
    Esta migración usa CREATE INDEX normal (sin CONCURRENTLY) para que funcione con Alembic.
    En producción, puede ejecutarse manualmente con CONCURRENTLY si es necesario.
    """
    connection = op.get_bind()
    inspector = inspect(connection)
    
    print("\n🚀 Iniciando migración de índices críticos de performance...")
    
    # ============================================
    # ÍNDICES CRÍTICOS: NOTIFICACIONES
    # Resuelve timeout de 57s en /api/v1/notificaciones/estadisticas/resumen
    # ============================================
    if _table_exists(inspector, 'notificaciones'):
        # Índice en estado (crítico para GROUP BY)
        index_name = 'idx_notificaciones_estado'
        if not _index_exists(inspector, 'notificaciones', index_name):
            if _column_exists(inspector, 'notificaciones', 'estado'):
                try:
                    # Crear índice (sin CONCURRENTLY para compatibilidad con transacciones de Alembic)
                    op.create_index(
                        index_name,
                        'notificaciones',
                        ['estado'],
                        unique=False
                    )
                    print(f"✅ Índice '{index_name}' creado en tabla 'notificaciones'")
                except Exception as e:
                    print(f"⚠️ Advertencia: No se pudo crear índice '{index_name}': {e}")
            else:
                print("ℹ️ Columna 'estado' no existe en 'notificaciones', omitiendo...")
        else:
            print(f"ℹ️ Índice '{index_name}' ya existe, omitiendo...")
        
        # Índice en leida (si existe la columna)
        index_name = 'idx_notificaciones_leida'
        if not _index_exists(inspector, 'notificaciones', index_name):
            if _column_exists(inspector, 'notificaciones', 'leida'):
                try:
                    # Índice parcial - usar SQL directo para WHERE clause
                    connection.execute(text(
                        f"CREATE INDEX IF NOT EXISTS {index_name} "
                        f"ON notificaciones (leida) WHERE leida IS NOT NULL"
                    ))
                    print(f"✅ Índice parcial '{index_name}' creado en tabla 'notificaciones'")
                except Exception as e:
                    print(f"⚠️ Advertencia: No se pudo crear índice '{index_name}': {e}")
            else:
                print("ℹ️ Columna 'leida' no existe en 'notificaciones', omitiendo...")
        else:
            print(f"ℹ️ Índice '{index_name}' ya existe, omitiendo...")
    else:
        print("ℹ️ Tabla 'notificaciones' no existe, omitiendo índices...")
    
    # ============================================
    # ÍNDICES CRÍTICOS: PAGOS_STAGING
    # Resuelve queries lentas en KPIs de pagos
    # ============================================
    if _table_exists(inspector, 'pagos_staging'):
        # Índice funcional para fecha_pago::timestamp (crítico para filtros de fecha)
        index_name = 'idx_pagos_staging_fecha_timestamp'
        if not _index_exists(inspector, 'pagos_staging', index_name):
            try:
                # Índice funcional - usar SQL directo para expresiones
                connection.execute(text(
                    f"CREATE INDEX IF NOT EXISTS {index_name} "
                    f"ON pagos_staging USING btree ((fecha_pago::timestamp)) "
                    f"WHERE fecha_pago IS NOT NULL AND fecha_pago != ''"
                ))
                print(f"✅ Índice funcional '{index_name}' creado en tabla 'pagos_staging'")
            except Exception as e:
                print(f"⚠️ Advertencia: No se pudo crear índice '{index_name}': {e}")
        else:
            print(f"ℹ️ Índice '{index_name}' ya existe, omitiendo...")
        
        # Índice funcional para monto_pagado::numeric
        index_name = 'idx_pagos_staging_monto_numeric'
        if not _index_exists(inspector, 'pagos_staging', index_name):
            try:
                # Índice funcional - usar SQL directo para expresiones
                connection.execute(text(
                    f"CREATE INDEX IF NOT EXISTS {index_name} "
                    f"ON pagos_staging USING btree ((monto_pagado::numeric)) "
                    f"WHERE monto_pagado IS NOT NULL AND monto_pagado != ''"
                ))
                print(f"✅ Índice funcional '{index_name}' creado en tabla 'pagos_staging'")
            except Exception as e:
                print(f"⚠️ Advertencia: No se pudo crear índice '{index_name}': {e}")
        else:
            print(f"ℹ️ Índice '{index_name}' ya existe, omitiendo...")
    else:
        print("ℹ️ Tabla 'pagos_staging' no existe, omitiendo índices...")
    
    # ============================================
    # ÍNDICES CRÍTICOS: CUOTAS
    # Resuelve queries de morosidad y KPIs
    # ============================================
    if _table_exists(inspector, 'cuotas'):
        # Índice compuesto para fecha_vencimiento + estado (crítico para queries de mora)
        index_name = 'idx_cuotas_vencimiento_estado'
        if not _index_exists(inspector, 'cuotas', index_name):
            if (_column_exists(inspector, 'cuotas', 'fecha_vencimiento') and 
                _column_exists(inspector, 'cuotas', 'estado')):
                try:
                    # Índice compuesto parcial - usar SQL directo
                    connection.execute(text(
                        f"CREATE INDEX IF NOT EXISTS {index_name} "
                        f"ON cuotas (fecha_vencimiento, estado) "
                        f"WHERE estado != 'PAGADO'"
                    ))
                    print(f"✅ Índice compuesto parcial '{index_name}' creado en tabla 'cuotas'")
                except Exception as e:
                    print(f"⚠️ Advertencia: No se pudo crear índice '{index_name}': {e}")
            else:
                print("ℹ️ Columnas requeridas no existen en 'cuotas', omitiendo...")
        else:
            print(f"ℹ️ Índice '{index_name}' ya existe, omitiendo...")
        
        # Índice en prestamo_id (ya debería existir, pero verificar)
        index_name = 'idx_cuotas_prestamo_id'
        if not _index_exists(inspector, 'cuotas', index_name):
            if _column_exists(inspector, 'cuotas', 'prestamo_id'):
                try:
                    op.create_index(
                        index_name,
                        'cuotas',
                        ['prestamo_id'],
                        unique=False
                    )
                    print(f"✅ Índice '{index_name}' creado en tabla 'cuotas'")
                except Exception as e:
                    print(f"⚠️ Advertencia: No se pudo crear índice '{index_name}': {e}")
            else:
                print("ℹ️ Columna 'prestamo_id' no existe en 'cuotas', omitiendo...")
        else:
            print(f"ℹ️ Índice '{index_name}' ya existe, omitiendo...")
    else:
        print("ℹ️ Tabla 'cuotas' no existe, omitiendo índices...")
    
    # ============================================
    # ÍNDICES CRÍTICOS: PRESTAMOS
    # Resuelve filtros frecuentes en dashboard
    # ============================================
    if _table_exists(inspector, 'prestamos'):
        # Índice en estado (crítico para filtros)
        index_name = 'idx_prestamos_estado'
        if not _index_exists(inspector, 'prestamos', index_name):
            if _column_exists(inspector, 'prestamos', 'estado'):
                try:
                    op.create_index(
                        index_name,
                        'prestamos',
                        ['estado'],
                        unique=False
                    )
                    print(f"✅ Índice '{index_name}' creado en tabla 'prestamos'")
                except Exception as e:
                    print(f"⚠️ Advertencia: No se pudo crear índice '{index_name}': {e}")
            else:
                print("ℹ️ Columna 'estado' no existe en 'prestamos', omitiendo...")
        else:
            print(f"ℹ️ Índice '{index_name}' ya existe, omitiendo...")
        
        # Índice en cedula (crítico para búsquedas por cliente)
        index_name = 'idx_prestamos_cedula'
        if not _index_exists(inspector, 'prestamos', index_name):
            if _column_exists(inspector, 'prestamos', 'cedula'):
                try:
                    op.create_index(
                        index_name,
                        'prestamos',
                        ['cedula'],
                        unique=False
                    )
                    print(f"✅ Índice '{index_name}' creado en tabla 'prestamos'")
                except Exception as e:
                    print(f"⚠️ Advertencia: No se pudo crear índice '{index_name}': {e}")
            else:
                print("ℹ️ Columna 'cedula' no existe en 'prestamos', omitiendo...")
        else:
            print(f"ℹ️ Índice '{index_name}' ya existe, omitiendo...")
    else:
        print("ℹ️ Tabla 'prestamos' no existe, omitiendo índices...")
    
    # Ejecutar ANALYZE para actualizar estadísticas
    try:
        print("\n📊 Actualizando estadísticas de tablas...")
        tables_to_analyze = ['notificaciones', 'pagos_staging', 'cuotas', 'prestamos']
        for table in tables_to_analyze:
            if _table_exists(inspector, table):
                try:
                    connection.execute(text(f"ANALYZE {table}"))
                    print(f"✅ ANALYZE ejecutado en '{table}'")
                except Exception as e:
                    print(f"⚠️ No se pudo ejecutar ANALYZE en '{table}': {e}")
    except Exception as e:
        print(f"⚠️ Advertencia al ejecutar ANALYZE: {e}")
    
    print("\n✅ Migración de índices críticos completada")
    print("📈 Impacto esperado: Reducción de timeouts de 57s a <500ms (114x mejora)")


def downgrade():
    """
    Eliminar índices críticos de performance (rollback seguro).
    """
    connection = op.get_bind()
    inspector = inspect(connection)
    
    print("\n🔄 Iniciando rollback de índices críticos...")
    
    indices_to_drop = [
        ('notificaciones', 'idx_notificaciones_estado'),
        ('notificaciones', 'idx_notificaciones_leida'),
        ('pagos_staging', 'idx_pagos_staging_fecha_timestamp'),
        ('pagos_staging', 'idx_pagos_staging_monto_numeric'),
        ('cuotas', 'idx_cuotas_vencimiento_estado'),
        ('cuotas', 'idx_cuotas_prestamo_id'),
        ('prestamos', 'idx_prestamos_estado'),
        ('prestamos', 'idx_prestamos_cedula'),
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
    
    print("\n✅ Rollback de índices críticos completado")

