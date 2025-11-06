#!/usr/bin/env python3
"""
Script para crear índices críticos de performance manualmente
Útil si las migraciones de Alembic no se ejecutaron correctamente
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, inspect
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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


def crear_indices():
    """Crear todos los índices críticos de performance"""
    engine = create_engine(settings.DATABASE_URL)
    inspector = inspect(engine)
    
    indices_creados = 0
    indices_omitidos = 0
    errores = []
    
    print("=" * 80)
    print("🚀 CREANDO ÍNDICES CRÍTICOS DE PERFORMANCE")
    print("=" * 80)
    print()
    
    with engine.connect() as connection:
        # ============================================
        # ÍNDICES: NOTIFICACIONES
        # ============================================
        if _table_exists(inspector, 'notificaciones'):
            indices_notificaciones = [
                ('idx_notificaciones_estado', ['estado']),
                ('idx_notificaciones_tipo', ['tipo']),
                ('idx_notificaciones_fecha_creacion', ['fecha_creacion']),
            ]
            
            for idx_name, columns in indices_notificaciones:
                if not _index_exists(inspector, 'notificaciones', idx_name):
                    if all(_column_exists(inspector, 'notificaciones', col) for col in columns):
                        try:
                            connection.execute(text(
                                f"CREATE INDEX IF NOT EXISTS {idx_name} ON notificaciones ({', '.join(columns)})"
                            ))
                            connection.commit()
                            print(f"✅ Índice '{idx_name}' creado en tabla 'notificaciones'")
                            indices_creados += 1
                        except Exception as e:
                            print(f"⚠️ Error creando índice '{idx_name}': {e}")
                            errores.append(f"{idx_name}: {e}")
                    else:
                        print(f"ℹ️ Columnas no existen para '{idx_name}', omitiendo...")
                else:
                    print(f"ℹ️ Índice '{idx_name}' ya existe, omitiendo...")
                    indices_omitidos += 1
        
        # ============================================
        # ÍNDICES: CUOTAS
        # ============================================
        if _table_exists(inspector, 'cuotas'):
            # Índice compuesto para fecha_vencimiento + estado
            idx_name = 'idx_cuotas_vencimiento_estado'
            if not _index_exists(inspector, 'cuotas', idx_name):
                if (_column_exists(inspector, 'cuotas', 'fecha_vencimiento') and 
                    _column_exists(inspector, 'cuotas', 'estado')):
                    try:
                        connection.execute(text(
                            f"CREATE INDEX IF NOT EXISTS {idx_name} "
                            f"ON cuotas (fecha_vencimiento, estado) "
                            f"WHERE estado != 'PAGADO'"
                        ))
                        connection.commit()
                        print(f"✅ Índice compuesto parcial '{idx_name}' creado en tabla 'cuotas'")
                        indices_creados += 1
                    except Exception as e:
                        print(f"⚠️ Error creando índice '{idx_name}': {e}")
                        errores.append(f"{idx_name}: {e}")
            
            # Índice en prestamo_id
            idx_name = 'idx_cuotas_prestamo_id'
            if not _index_exists(inspector, 'cuotas', idx_name):
                if _column_exists(inspector, 'cuotas', 'prestamo_id'):
                    try:
                        connection.execute(text(
                            f"CREATE INDEX IF NOT EXISTS {idx_name} ON cuotas (prestamo_id)"
                        ))
                        connection.commit()
                        print(f"✅ Índice '{idx_name}' creado en tabla 'cuotas'")
                        indices_creados += 1
                    except Exception as e:
                        print(f"⚠️ Error creando índice '{idx_name}': {e}")
                        errores.append(f"{idx_name}: {e}")
            
            # Índice funcional para GROUP BY
            idx_name = 'idx_cuotas_extract_year_month'
            if not _index_exists(inspector, 'cuotas', idx_name):
                if _column_exists(inspector, 'cuotas', 'fecha_vencimiento'):
                    try:
                        connection.execute(text(
                            f"CREATE INDEX IF NOT EXISTS {idx_name} "
                            f"ON cuotas USING btree ("
                            f"  EXTRACT(YEAR FROM fecha_vencimiento), "
                            f"  EXTRACT(MONTH FROM fecha_vencimiento)"
                            f") "
                            f"WHERE fecha_vencimiento IS NOT NULL"
                        ))
                        connection.commit()
                        print(f"✅ Índice funcional '{idx_name}' creado en tabla 'cuotas'")
                        indices_creados += 1
                    except Exception as e:
                        print(f"⚠️ Error creando índice '{idx_name}': {e}")
                        errores.append(f"{idx_name}: {e}")
        
        # ============================================
        # ÍNDICES: PRESTAMOS
        # ============================================
        if _table_exists(inspector, 'prestamos'):
            indices_prestamos = [
                ('idx_prestamos_estado', ['estado']),
                ('idx_prestamos_cedula', ['cedula']),
                # ✅ OPTIMIZACIÓN PRIORIDAD 1: Índices para dashboard
                ('idx_prestamos_estado_fecha_aprobacion', ['estado', 'fecha_aprobacion']),
                ('idx_prestamos_estado_fecha_registro', ['estado', 'fecha_registro']),
            ]
            
            for idx_name, columns in indices_prestamos:
                if not _index_exists(inspector, 'prestamos', idx_name):
                    if all(_column_exists(inspector, 'prestamos', col) for col in columns):
                        try:
                            connection.execute(text(
                                f"CREATE INDEX IF NOT EXISTS {idx_name} ON prestamos ({', '.join(columns)})"
                            ))
                            connection.commit()
                            print(f"✅ Índice '{idx_name}' creado en tabla 'prestamos'")
                            indices_creados += 1
                        except Exception as e:
                            print(f"⚠️ Error creando índice '{idx_name}': {e}")
                            errores.append(f"{idx_name}: {e}")
                    else:
                        print(f"ℹ️ Columnas no existen para '{idx_name}', omitiendo...")
                else:
                    print(f"ℹ️ Índice '{idx_name}' ya existe, omitiendo...")
                    indices_omitidos += 1
        
        # ============================================
        # ÍNDICES: PAGOS
        # ============================================
        if _table_exists(inspector, 'pagos'):
            indices_pagos = [
                ('ix_pagos_fecha_registro', ['fecha_registro']),
                # ✅ OPTIMIZACIÓN PRIORIDAD 1: Índices para dashboard
                ('idx_pagos_fecha_pago_activo', ['fecha_pago', 'activo']),
                ('idx_pagos_fecha_pago_monto', ['fecha_pago', 'monto_pagado']),
            ]
            
            for idx_name, columns in indices_pagos:
                if not _index_exists(inspector, 'pagos', idx_name):
                    if all(_column_exists(inspector, 'pagos', col) for col in columns):
                        try:
                            connection.execute(text(
                                f"CREATE INDEX IF NOT EXISTS {idx_name} ON pagos ({', '.join(columns)})"
                            ))
                            connection.commit()
                            print(f"✅ Índice '{idx_name}' creado en tabla 'pagos'")
                            indices_creados += 1
                        except Exception as e:
                            print(f"⚠️ Error creando índice '{idx_name}': {e}")
                            errores.append(f"{idx_name}: {e}")
                    else:
                        print(f"ℹ️ Columnas no existen para '{idx_name}', omitiendo...")
                else:
                    print(f"ℹ️ Índice '{idx_name}' ya existe, omitiendo...")
                    indices_omitidos += 1
        
        # ============================================
        # ÍNDICES: PAGOS_STAGING (si existe)
        # ============================================
        if _table_exists(inspector, 'pagos_staging'):
            # Índice funcional para fecha_pago::timestamp
            idx_name = 'idx_pagos_staging_fecha_timestamp'
            if not _index_exists(inspector, 'pagos_staging', idx_name):
                if _column_exists(inspector, 'pagos_staging', 'fecha_pago'):
                    try:
                        connection.execute(text(
                            f"CREATE INDEX IF NOT EXISTS {idx_name} "
                            f"ON pagos_staging USING btree ((fecha_pago::timestamp)) "
                            f"WHERE fecha_pago IS NOT NULL AND fecha_pago != ''"
                        ))
                        connection.commit()
                        print(f"✅ Índice funcional '{idx_name}' creado en tabla 'pagos_staging'")
                        indices_creados += 1
                    except Exception as e:
                        print(f"⚠️ Error creando índice '{idx_name}': {e}")
                        errores.append(f"{idx_name}: {e}")
                else:
                    print(f"ℹ️ Columna no existe para '{idx_name}', omitiendo...")
            else:
                print(f"ℹ️ Índice '{idx_name}' ya existe, omitiendo...")
                indices_omitidos += 1
            
            # Índice funcional para monto_pagado::numeric
            idx_name = 'idx_pagos_staging_monto_numeric'
            if not _index_exists(inspector, 'pagos_staging', idx_name):
                if _column_exists(inspector, 'pagos_staging', 'monto_pagado'):
                    try:
                        connection.execute(text(
                            f"CREATE INDEX IF NOT EXISTS {idx_name} "
                            f"ON pagos_staging USING btree ((monto_pagado::numeric)) "
                            f"WHERE monto_pagado IS NOT NULL AND monto_pagado != ''"
                        ))
                        connection.commit()
                        print(f"✅ Índice funcional '{idx_name}' creado en tabla 'pagos_staging'")
                        indices_creados += 1
                    except Exception as e:
                        print(f"⚠️ Error creando índice '{idx_name}': {e}")
                        errores.append(f"{idx_name}: {e}")
                else:
                    print(f"ℹ️ Columna no existe para '{idx_name}', omitiendo...")
            else:
                print(f"ℹ️ Índice '{idx_name}' ya existe, omitiendo...")
                indices_omitidos += 1
            
            # Índice funcional para EXTRACT(YEAR FROM fecha_pago::timestamp)
            idx_name = 'idx_pagos_staging_extract_year'
            if not _index_exists(inspector, 'pagos_staging', idx_name):
                if _column_exists(inspector, 'pagos_staging', 'fecha_pago'):
                    try:
                        connection.execute(text(
                            f"CREATE INDEX IF NOT EXISTS {idx_name} "
                            f"ON pagos_staging USING btree (EXTRACT(YEAR FROM fecha_pago::timestamp)) "
                            f"WHERE fecha_pago IS NOT NULL AND fecha_pago != '' AND fecha_pago ~ '^\\d{{4}}-\\d{{2}}-\\d{{2}}'"
                        ))
                        connection.commit()
                        print(f"✅ Índice funcional '{idx_name}' creado para GROUP BY YEAR")
                        indices_creados += 1
                    except Exception as e:
                        print(f"⚠️ Error creando índice '{idx_name}': {e}")
                        errores.append(f"{idx_name}: {e}")
                else:
                    print(f"ℹ️ Columna no existe para '{idx_name}', omitiendo...")
            else:
                print(f"ℹ️ Índice '{idx_name}' ya existe, omitiendo...")
                indices_omitidos += 1
            
            # Índice compuesto funcional para EXTRACT(YEAR, MONTH FROM fecha_pago::timestamp)
            idx_name = 'idx_pagos_staging_extract_year_month'
            if not _index_exists(inspector, 'pagos_staging', idx_name):
                if _column_exists(inspector, 'pagos_staging', 'fecha_pago'):
                    try:
                        connection.execute(text(
                            f"CREATE INDEX IF NOT EXISTS {idx_name} "
                            f"ON pagos_staging USING btree ("
                            f"  EXTRACT(YEAR FROM fecha_pago::timestamp), "
                            f"  EXTRACT(MONTH FROM fecha_pago::timestamp)"
                            f") "
                            f"WHERE fecha_pago IS NOT NULL AND fecha_pago != '' AND fecha_pago ~ '^\\d{{4}}-\\d{{2}}-\\d{{2}}'"
                        ))
                        connection.commit()
                        print(f"✅ Índice compuesto funcional '{idx_name}' creado para GROUP BY YEAR, MONTH")
                        indices_creados += 1
                    except Exception as e:
                        print(f"⚠️ Error creando índice '{idx_name}': {e}")
                        errores.append(f"{idx_name}: {e}")
                else:
                    print(f"ℹ️ Columna no existe para '{idx_name}', omitiendo...")
            else:
                print(f"ℹ️ Índice '{idx_name}' ya existe, omitiendo...")
                indices_omitidos += 1
        
        # Ejecutar ANALYZE para actualizar estadísticas
        try:
            print("\n📊 Actualizando estadísticas de tablas...")
            tables_to_analyze = ['notificaciones', 'cuotas', 'prestamos', 'pagos', 'pagos_staging']
            for table in tables_to_analyze:
                if _table_exists(inspector, table):
                    try:
                        connection.execute(text(f"ANALYZE {table}"))
                        connection.commit()
                        print(f"✅ ANALYZE ejecutado en '{table}'")
                    except Exception as e:
                        print(f"⚠️ No se pudo ejecutar ANALYZE en '{table}': {e}")
        except Exception as e:
            print(f"⚠️ Advertencia al ejecutar ANALYZE: {e}")
    
    print()
    print("=" * 80)
    print("📊 RESUMEN")
    print("=" * 80)
    print(f"✅ Índices creados: {indices_creados}")
    print(f"ℹ️ Índices ya existentes: {indices_omitidos}")
    if errores:
        print(f"❌ Errores: {len(errores)}")
        for error in errores:
            print(f"   - {error}")
    print()
    
    if indices_creados > 0:
        print("✅ Índices creados exitosamente")
        print("📈 Impacto esperado: Mejora significativa en tiempos de queries")
    else:
        print("ℹ️ No se crearon nuevos índices (ya existen o hay errores)")


if __name__ == "__main__":
    try:
        crear_indices()
    except Exception as e:
        logger.error(f"Error ejecutando script: {e}", exc_info=True)
        sys.exit(1)

