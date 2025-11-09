#!/usr/bin/env python3
"""
Script para verificar índices en la base de datos PostgreSQL

Este script analiza los índices existentes y recomienda índices faltantes
para mejorar el performance de las queries más comunes.

Uso:
    python backend/scripts/verificar_indices_bd.py
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from sqlalchemy import text
from app.db.session import SessionLocal

# Índices recomendados basados en las queries más comunes
INDICES_RECOMENDADOS = {
    "prestamos": [
        {
            "nombre": "idx_prestamos_estado",
            "columnas": ["estado"],
            "descripcion": "Filtro por estado (APROBADO, PENDIENTE, etc.)",
            "prioridad": "ALTA",
        },
        {
            "nombre": "idx_prestamos_fecha_registro",
            "columnas": ["fecha_registro"],
            "descripcion": "Filtros y ordenamiento por fecha de registro",
            "prioridad": "ALTA",
        },
        {
            "nombre": "idx_prestamos_cedula",
            "columnas": ["cedula"],
            "descripcion": "JOINs con tabla clientes",
            "prioridad": "MEDIA",
        },
        {
            "nombre": "idx_prestamos_usuario_proponente",
            "columnas": ["usuario_proponente"],
            "descripcion": "Filtros por analista",
            "prioridad": "MEDIA",
        },
    ],
    "cuotas": [
        {
            "nombre": "idx_cuotas_prestamo_id",
            "columnas": ["prestamo_id"],
            "descripcion": "JOINs con tabla prestamos",
            "prioridad": "ALTA",
        },
        {
            "nombre": "idx_cuotas_estado",
            "columnas": ["estado"],
            "descripcion": "Filtro por estado (PAGADO, PENDIENTE, etc.)",
            "prioridad": "ALTA",
        },
        {
            "nombre": "idx_cuotas_fecha_vencimiento",
            "columnas": ["fecha_vencimiento"],
            "descripcion": "Filtros por fechas de vencimiento",
            "prioridad": "ALTA",
        },
        {
            "nombre": "idx_cuotas_fecha_vencimiento_funcional",
            "columnas": ["EXTRACT(YEAR FROM fecha_vencimiento)", "EXTRACT(MONTH FROM fecha_vencimiento)"],
            "descripcion": "Índice funcional para GROUP BY por año/mes",
            "prioridad": "ALTA",
            "tipo": "funcional",
            "sql": "CREATE INDEX IF NOT EXISTS idx_cuotas_fecha_vencimiento_funcional ON cuotas (EXTRACT(YEAR FROM fecha_vencimiento), EXTRACT(MONTH FROM fecha_vencimiento));",
        },
    ],
    "pagos_staging": [
        {
            "nombre": "idx_pagos_staging_fecha_pago",
            "columnas": ["fecha_pago"],
            "descripcion": "Filtros por fecha de pago",
            "prioridad": "ALTA",
        },
        {
            "nombre": "idx_pagos_staging_fecha_pago_funcional",
            "columnas": ["EXTRACT(YEAR FROM fecha_pago::timestamp)", "EXTRACT(MONTH FROM fecha_pago::timestamp)"],
            "descripcion": "Índice funcional para GROUP BY por año/mes",
            "prioridad": "ALTA",
            "tipo": "funcional",
            "sql": "CREATE INDEX IF NOT EXISTS idx_pagos_staging_fecha_pago_funcional ON pagos_staging (EXTRACT(YEAR FROM fecha_pago::timestamp), EXTRACT(MONTH FROM fecha_pago::timestamp)) WHERE fecha_pago IS NOT NULL AND fecha_pago != '';",
        },
        {
            "nombre": "idx_pagos_staging_conciliado",
            "columnas": ["conciliado"],
            "descripcion": "Filtros por estado de conciliación",
            "prioridad": "MEDIA",
        },
    ],
    "clientes": [
        {
            "nombre": "idx_clientes_cedula",
            "columnas": ["cedula"],
            "descripcion": "Búsquedas y JOINs por cédula",
            "prioridad": "ALTA",
        },
        {
            "nombre": "idx_clientes_fecha_registro",
            "columnas": ["fecha_registro"],
            "descripcion": "Ordenamiento y filtros por fecha",
            "prioridad": "MEDIA",
        },
        {
            "nombre": "idx_clientes_estado",
            "columnas": ["estado"],
            "descripcion": "Filtros por estado",
            "prioridad": "MEDIA",
        },
    ],
    "dashboard_morosidad_mensual": [
        {
            "nombre": "idx_dashboard_morosidad_año_mes",
            "columnas": ["año", "mes"],
            "descripcion": "Índice compuesto para queries de evolución mensual",
            "prioridad": "ALTA",
        },
    ],
}


def obtener_indices_existentes(db):
    """Obtener lista de índices existentes en la base de datos"""
    query = text("""
        SELECT
            schemaname,
            tablename,
            indexname,
            indexdef
        FROM pg_indexes
        WHERE schemaname = 'public'
        ORDER BY tablename, indexname
    """)
    result = db.execute(query)
    indices = {}
    for row in result:
        tabla = row.tablename
        if tabla not in indices:
            indices[tabla] = []
        indices[tabla].append({
            "nombre": row.indexname,
            "definicion": row.indexdef,
        })
    return indices


def verificar_indice_existe(indices_existentes, tabla, nombre_indice):
    """Verificar si un índice existe"""
    if tabla not in indices_existentes:
        return False
    return any(idx["nombre"] == nombre_indice for idx in indices_existentes[tabla])


def analizar_tabla(db, tabla):
    """Analizar tamaño y estadísticas de una tabla"""
    try:
        # Obtener número de filas
        count_query = text(f"SELECT COUNT(*) FROM {tabla}")
        count_result = db.execute(count_query)
        num_filas = count_result.scalar()

        # Obtener tamaño de la tabla
        size_query = text(f"""
            SELECT pg_size_pretty(pg_total_relation_size('{tabla}')) as size
        """)
        size_result = db.execute(size_query)
        tamaño = size_result.scalar()

        return {
            "num_filas": num_filas,
            "tamaño": tamaño,
        }
    except Exception as e:
        return {
            "num_filas": 0,
            "tamaño": "N/A",
            "error": str(e),
        }


def main():
    """Función principal"""
    print("=" * 80)
    print("🔍 VERIFICACIÓN DE ÍNDICES EN BASE DE DATOS")
    print("=" * 80)
    print()

    db = SessionLocal()
    try:
        # Obtener índices existentes
        print("📊 Obteniendo índices existentes...")
        indices_existentes = obtener_indices_existentes(db)
        print(f"✅ Encontrados índices en {len(indices_existentes)} tablas\n")

        # Analizar cada tabla recomendada
        indices_faltantes = []
        indices_existentes_lista = []

        for tabla, indices_recomendados in INDICES_RECOMENDADOS.items():
            print(f"\n📋 Tabla: {tabla}")
            print("-" * 80)

            # Analizar tabla
            stats = analizar_tabla(db, tabla)
            if "error" in stats:
                print(f"⚠️  Error analizando tabla: {stats['error']}")
                continue

            print(f"   Filas: {stats['num_filas']:,}")
            print(f"   Tamaño: {stats['tamaño']}")

            # Verificar índices de la tabla
            if tabla in indices_existentes:
                print(f"   Índices existentes: {len(indices_existentes[tabla])}")
                for idx in indices_existentes[tabla]:
                    indices_existentes_lista.append({
                        "tabla": tabla,
                        "indice": idx["nombre"],
                    })
            else:
                print(f"   ⚠️  No se encontraron índices existentes")

            # Verificar índices recomendados
            print(f"\n   Índices recomendados:")
            for idx_rec in indices_recomendados:
                nombre = idx_rec["nombre"]
                existe = verificar_indice_existe(indices_existentes, tabla, nombre)

                if existe:
                    print(f"   ✅ {nombre} - {idx_rec['descripcion']} (Prioridad: {idx_rec['prioridad']})")
                else:
                    print(f"   ❌ {nombre} - {idx_rec['descripcion']} (Prioridad: {idx_rec['prioridad']})")
                    indices_faltantes.append({
                        "tabla": tabla,
                        "indice": idx_rec,
                    })

        # Resumen
        print("\n" + "=" * 80)
        print("📊 RESUMEN")
        print("=" * 80)
        print(f"Índices existentes verificados: {len(indices_existentes_lista)}")
        print(f"Índices faltantes recomendados: {len(indices_faltantes)}")

        if indices_faltantes:
            print("\n⚠️  ÍNDICES FALTANTES (Prioridad ALTA):")
            print("-" * 80)
            alta_prioridad = [idx for idx in indices_faltantes if idx["indice"]["prioridad"] == "ALTA"]
            for idx in alta_prioridad:
                print(f"❌ {idx['tabla']}.{idx['indice']['nombre']}")
                print(f"   Descripción: {idx['indice']['descripcion']}")
                if "sql" in idx["indice"]:
                    print(f"   SQL: {idx['indice']['sql']}")
                print()

            if alta_prioridad:
                print("\n💡 RECOMENDACIÓN:")
                print("   Ejecutar los índices de prioridad ALTA para mejorar significativamente el rendimiento.")
                print("   Los índices funcionales son especialmente importantes para queries con GROUP BY.")
        else:
            print("\n✅ Todos los índices recomendados están presentes")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
