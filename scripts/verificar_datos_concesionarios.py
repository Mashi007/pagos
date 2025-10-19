#!/usr/bin/env python3
"""
Script para verificar los datos reales de concesionarios en la base de datos
"""
import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

# Configuración de la base de datos
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://pagos_admin:***@dpg-d3l8tkur433s738ooph0-a.oregon-postgres.render.com/pagos_db_zjer?sslmode=require')

def verificar_concesionarios():
    """Verificar los datos reales de concesionarios"""
    try:
        # Conectar a la base de datos
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("🔍 VERIFICANDO DATOS DE CONCESIONARIOS")
        print("=" * 50)
        
        # 1. Contar total de concesionarios
        cursor.execute("SELECT COUNT(*) as total FROM concesionarios")
        total = cursor.fetchone()['total']
        print(f"📊 Total de concesionarios: {total}")
        
        # 2. Verificar estructura de la tabla
        cursor.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'concesionarios'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        print(f"\n📋 Estructura de la tabla 'concesionarios':")
        for col in columns:
            print(f"   - {col['column_name']}: {col['data_type']} ({'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'})")
        
        # 3. Mostrar algunos registros de ejemplo
        cursor.execute("""
            SELECT id, nombre, activo, created_at, updated_at 
            FROM concesionarios 
            ORDER BY id 
            LIMIT 10
        """)
        registros = cursor.fetchall()
        
        print(f"\n📝 Primeros 10 registros:")
        for reg in registros:
            print(f"   ID: {reg['id']}, Nombre: '{reg['nombre']}', Activo: {reg['activo']}")
        
        # 4. Verificar si hay datos genéricos vs reales
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN nombre LIKE 'Concesionario #%' THEN 1 END) as genericos,
                COUNT(CASE WHEN nombre NOT LIKE 'Concesionario #%' THEN 1 END) as reales
            FROM concesionarios
        """)
        stats = cursor.fetchone()
        
        print(f"\n📊 Análisis de datos:")
        print(f"   - Total: {stats['total']}")
        print(f"   - Genéricos (Concesionario #XX): {stats['genericos']}")
        print(f"   - Reales: {stats['reales']}")
        
        # 5. Mostrar algunos nombres reales si existen
        cursor.execute("""
            SELECT nombre 
            FROM concesionarios 
            WHERE nombre NOT LIKE 'Concesionario #%'
            LIMIT 5
        """)
        nombres_reales = cursor.fetchall()
        
        if nombres_reales:
            print(f"\n✅ Nombres reales encontrados:")
            for nombre in nombres_reales:
                print(f"   - {nombre['nombre']}")
        else:
            print(f"\n❌ No se encontraron nombres reales (solo datos genéricos)")
        
        # 6. Verificar concesionarios activos
        cursor.execute("""
            SELECT COUNT(*) as activos 
            FROM concesionarios 
            WHERE activo = true
        """)
        activos = cursor.fetchone()['activos']
        print(f"\n🟢 Concesionarios activos: {activos}")
        
        cursor.close()
        conn.close()
        
        print(f"\n✅ Verificación completada")
        
    except Exception as e:
        print(f"❌ Error verificando concesionarios: {e}")
        return False
    
    return True

if __name__ == "__main__":
    verificar_concesionarios()
