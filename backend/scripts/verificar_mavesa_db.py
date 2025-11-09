#!/usr/bin/env python3
"""
Script para verificar concesionarios en la base de datos
Especialmente busca "Mavesa"
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

# Configuración de la base de datos
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://pagos_admin:***@dpg-d3l8tkur433s738ooph0-a.oregon-postgres.render.com/pagos_db_zjer?sslmode=require'
)

def verificar_concesionarios():
    """Verificar los concesionarios en la base de datos"""
    try:
        # Conectar a la base de datos
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        print("=" * 80)
        print("VERIFICACIÓN DE CONCESIONARIOS EN BASE DE DATOS")
        print("=" * 80)

        # 1. Verificar todos los concesionarios
        print("\n1. TODOS LOS CONCESIONARIOS:")
        print("-" * 80)
        cursor.execute("""
            SELECT id, nombre, activo, created_at, updated_at
            FROM concesionarios
            ORDER BY id
        """)
        todos = cursor.fetchall()

        if todos:
            for row in todos:
                estado = "✅ ACTIVO" if row['activo'] else "❌ INACTIVO"
                created = row['created_at'].strftime('%Y-%m-%d %H:%M:%S') if row['created_at'] else 'NULL'
                print(f"ID: {row['id']:3d} | {row['nombre']:30s} | {estado} | Creado: {created}")
        else:
            print("⚠️ NO HAY CONCESIONARIOS EN LA BASE DE DATOS")

        # 2. Buscar específicamente "Mavesa"
        print("\n2. BÚSQUEDA DE 'MAVESA':")
        print("-" * 80)
        cursor.execute("""
            SELECT id, nombre, activo, created_at, updated_at
            FROM concesionarios
            WHERE LOWER(nombre) LIKE '%mavesa%'
            ORDER BY id
        """)
        mavesa = cursor.fetchall()

        if mavesa:
            print(f"✅ ENCONTRADOS {len(mavesa)} CONCESIONARIOS CON 'MAVESA'")
            for row in mavesa:
                estado = "✅ ACTIVO" if row['activo'] else "❌ INACTIVO"
                created = row['created_at'].strftime('%Y-%m-%d %H:%M:%S') if row['created_at'] else 'NULL'
                print(f"ID: {row['id']:3d} | {row['nombre']:30s} | {estado} | Creado: {created}")
        else:
            print("❌ NO SE ENCONTRÓ 'MAVESA' EN LOS CONCESIONARIOS")

        # 3. Estadísticas
        print("\n3. ESTADÍSTICAS:")
        print("-" * 80)
        cursor.execute("SELECT COUNT(*) as total FROM concesionarios")
        total = cursor.fetchone()['total']
        print(f"Total de concesionarios: {total}")

        cursor.execute("SELECT COUNT(*) as activos FROM concesionarios WHERE activo = true")
        activos = cursor.fetchone()['activos']
        print(f"Concesionarios activos: {activos}")

        cursor.execute("SELECT COUNT(*) as inactivos FROM concesionarios WHERE activo = false")
        inactivos = cursor.fetchone()['inactivos']
        print(f"Concesionarios inactivos: {inactivos}")

        # 4. Verificar columnas
        print("\n4. ESTRUCTURA DE LA TABLA:")
        print("-" * 80)
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'concesionarios'
            ORDER BY ordinal_position
        """)
        columnas = cursor.fetchall()
        for col in columnas:
            nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
            print(f"{col['column_name']:20s} | {col['data_type']:20s} | {nullable}")

        # 5. Verificar timestamps
        print("\n5. VERIFICACIÓN DE TIMESTAMPS:")
        print("-" * 80)
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(created_at) as con_created_at,
                COUNT(updated_at) as con_updated_at
            FROM concesionarios
        """)
        timestamps = cursor.fetchone()
        print(f"Total registros: {timestamps['total']}")
        print(f"Con created_at: {timestamps['con_created_at']}")
        print(f"Con updated_at: {timestamps['con_updated_at']}")

        conn.close()

        print("\n" + "=" * 80)
        print("VERIFICACIÓN COMPLETADA")
        print("=" * 80)

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verificar_concesionarios()
