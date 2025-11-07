#!/usr/bin/env python3
"""
Script para verificar conexión a la base de datos de Render desde el terminal
"""

import sys
import os
from urllib.parse import quote_plus

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("❌ psycopg2 no está instalado.")
    print("   Instala con: pip install psycopg2-binary")
    sys.exit(1)

# Datos de conexión de Render
HOST = "dpg-d318tkur433s738oopho-a.oregon-postgres.render.com"
PORT = 5432
DATABASE = "pagos_db_zjer"
USERNAME = "pagos_admin"
PASSWORD = "F310LGHBnP8NBhojFwpA6vCwCngGUrGt"

def test_connection():
    """Prueba la conexión a la base de datos de Render"""
    
    print("=" * 80)
    print("VERIFICACIÓN DE CONEXIÓN A RENDER POSTGRESQL")
    print("=" * 80)
    
    print(f"\n📊 Parámetros de conexión:")
    print(f"   Host: {HOST}")
    print(f"   Port: {PORT}")
    print(f"   Database: {DATABASE}")
    print(f"   Username: {USERNAME}")
    print(f"   Password: {'*' * len(PASSWORD)}")
    
    # Construir URL de conexión
    # Codificar la contraseña por si tiene caracteres especiales
    password_encoded = quote_plus(PASSWORD)
    database_url = f"postgresql://{USERNAME}:{password_encoded}@{HOST}:{PORT}/{DATABASE}?sslmode=require"
    
    print(f"\n🔗 URL de conexión (oculta): postgresql://{USERNAME}:***@{HOST}:{PORT}/{DATABASE}?sslmode=require")
    
    print("\n" + "=" * 80)
    print("1. PRUEBA DE CONECTIVIDAD (sin SSL)")
    print("=" * 80)
    
    try:
        # Primera prueba sin SSL explícito
        conn = psycopg2.connect(
            host=HOST,
            port=PORT,
            database=DATABASE,
            user=USERNAME,
            password=PASSWORD,
            connect_timeout=10
        )
        print("✅ Conexión exitosa (sin SSL explícito)")
        conn.close()
    except psycopg2.OperationalError as e:
        print(f"❌ Error de conexión (sin SSL): {e}")
        print("   Intentando con SSL...")
    except Exception as e:
        print(f"❌ Error inesperado: {type(e).__name__}: {e}")
    
    print("\n" + "=" * 80)
    print("2. PRUEBA DE CONECTIVIDAD (con SSL prefer)")
    print("=" * 80)
    
    try:
        # Segunda prueba con SSL prefer (más flexible)
        conn = psycopg2.connect(
            host=HOST,
            port=PORT,
            database=DATABASE,
            user=USERNAME,
            password=PASSWORD,
            sslmode='prefer',
            connect_timeout=10
        )
        print("✅ Conexión exitosa (con SSL)")
        
        # Ejecutar query de prueba
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✅ Versión PostgreSQL: {version.split(',')[0]}")
        
        cursor.execute("SELECT current_database();")
        db_name = cursor.fetchone()[0]
        print(f"✅ Base de datos actual: {db_name}")
        
        cursor.execute("SELECT current_user;")
        user = cursor.fetchone()[0]
        print(f"✅ Usuario actual: {user}")
        
        # Contar tablas
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        table_count = cursor.fetchone()[0]
        print(f"✅ Tablas en esquema public: {table_count}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 80)
        print("✅ VERIFICACIÓN COMPLETA: La conexión funciona correctamente")
        print("=" * 80)
        return True
        
    except psycopg2.OperationalError as e:
        print(f"❌ Error de conexión (con SSL prefer): {e}")
        
        # Intentar con allow (sin verificar certificado)
        print("\n" + "=" * 80)
        print("3. PRUEBA DE CONECTIVIDAD (con SSL allow - sin verificar certificado)")
        print("=" * 80)
        
        try:
            conn = psycopg2.connect(
                host=HOST,
                port=PORT,
                database=DATABASE,
                user=USERNAME,
                password=PASSWORD,
                sslmode='allow',
                connect_timeout=10
            )
            print("✅ Conexión exitosa (con SSL allow)")
            
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f"✅ Versión PostgreSQL: {version.split(',')[0]}")
            
            cursor.execute("SELECT current_database();")
            db_name = cursor.fetchone()[0]
            print(f"✅ Base de datos actual: {db_name}")
            
            cursor.close()
            conn.close()
            
            print("\n" + "=" * 80)
            print("✅ VERIFICACIÓN COMPLETA: La conexión funciona con SSL allow")
            print("=" * 80)
            return True
        except Exception as e2:
            print(f"❌ Error de conexión (con SSL allow): {e2}")
            print("\n💡 Posibles causas:")
            print("   - El hostname puede estar incorrecto")
            print("   - El puerto puede estar bloqueado por firewall")
            print("   - Las credenciales pueden estar incorrectas")
            print("   - La base de datos puede no permitir conexiones externas")
            print("   - Problema de configuración SSL en Render")
            return False
    except Exception as e:
        print(f"❌ Error inesperado: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)

