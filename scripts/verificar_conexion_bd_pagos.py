#!/usr/bin/env python3
"""
Script de verificación de conexión a la base de datos "pagos"
Verifica:
1. Que la conexión esté activa
2. El nombre de la base de datos actual
3. Las tablas disponibles
4. Si existe la tabla pagos_staging
"""

import os
import sys
from pathlib import Path

# Agregar el directorio backend al path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

def obtener_nombre_bd(database_url: str) -> str:
    """Extrae el nombre de la base de datos de la URL"""
    try:
        # Formato: postgresql://user:password@host:port/dbname
        if '@' in database_url:
            parte_final = database_url.split('@')[1]
            if '/' in parte_final:
                db_name = parte_final.split('/')[-1]
                # Limpiar parámetros adicionales
                if '?' in db_name:
                    db_name = db_name.split('?')[0]
                return db_name
        return "No se pudo determinar"
    except Exception:
        return "Error al extraer"

def verificar_conexion():
    """Verifica la conexión a la base de datos y muestra información detallada"""
    
    print("=" * 80)
    print("VERIFICACIÓN DE CONEXIÓN A BASE DE DATOS 'pagos'")
    print("=" * 80)
    
    # Obtener DATABASE_URL del entorno
    database_url = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/pagos_db")
    
    # Mostrar URL de forma segura (ocultando credenciales)
    if '@' in database_url:
        partes = database_url.split('@')
        credenciales = partes[0].split('://')[1] if '://' in partes[0] else partes[0]
        usuario = credenciales.split(':')[0] if ':' in credenciales else credenciales
        resto = partes[1] if len(partes) > 1 else ""
        url_segura = f"postgresql://{usuario}:***@{resto}"
    else:
        url_segura = database_url
    
    print(f"\n📊 DATABASE_URL configurada:")
    print(f"   {url_segura}")
    
    nombre_bd = obtener_nombre_bd(database_url)
    print(f"\n📁 Nombre de base de datos detectado: {nombre_bd}")
    
    try:
        # Crear engine
        engine = create_engine(database_url, pool_pre_ping=True)
        
        # Crear sesión
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        print("\n" + "=" * 80)
        print("1. VERIFICACIÓN DE CONEXIÓN")
        print("=" * 80)
        
        # Test básico de conexión
        try:
            resultado = db.execute(text("SELECT 1"))
            resultado.scalar()
            print("✅ Conexión a la base de datos: EXITOSA")
        except Exception as e:
            print(f"❌ Error en conexión básica: {e}")
            db.close()
            return False
        
        # Verificar nombre de BD real
        try:
            resultado = db.execute(text("SELECT current_database()"))
            bd_real = resultado.scalar()
            print(f"✅ Nombre de base de datos actual: {bd_real}")
            
            if bd_real.lower() != "pagos":
                print(f"⚠️  ADVERTENCIA: Se esperaba BD 'pagos', pero está conectado a '{bd_real}'")
            else:
                print(f"✅ Confirmado: Conectado a la base de datos 'pagos'")
        except Exception as e:
            print(f"⚠️  No se pudo obtener el nombre de la BD: {e}")
        
        # Verificar versión de PostgreSQL
        try:
            resultado = db.execute(text("SELECT version()"))
            version = resultado.scalar()
            print(f"📌 Versión PostgreSQL: {version.split(',')[0]}")
        except Exception as e:
            print(f"⚠️  No se pudo obtener la versión: {e}")
        
        print("\n" + "=" * 80)
        print("2. VERIFICACIÓN DE TABLAS")
        print("=" * 80)
        
        # Obtener todas las tablas
        inspector = inspect(engine)
        tablas = inspector.get_table_names()
        
        print(f"\n📋 Total de tablas en la base de datos: {len(tablas)}")
        
        # Verificar si existe pagos_staging
        if "pagos_staging" in tablas:
            print("✅ Tabla 'pagos_staging': EXISTE")
            
            # Obtener información de la tabla
            try:
                columnas = inspector.get_columns("pagos_staging")
                print(f"   - Columnas: {len(columnas)}")
                
                # Mostrar columnas principales
                nombres_columnas = [col['name'] for col in columnas]
                print(f"   - Columnas principales: {', '.join(nombres_columnas[:10])}")
                
                # Contar registros
                resultado = db.execute(text("SELECT COUNT(*) FROM pagos_staging"))
                count = resultado.scalar()
                print(f"   - Registros: {count}")
                
            except Exception as e:
                print(f"   ⚠️  Error al obtener información: {e}")
        else:
            print("❌ Tabla 'pagos_staging': NO EXISTE")
            print("\n📋 Tablas disponibles (primeras 20):")
            for i, tabla in enumerate(tablas[:20], 1):
                print(f"   {i}. {tabla}")
            if len(tablas) > 20:
                print(f"   ... y {len(tablas) - 20} más")
        
        # Verificar otras tablas relacionadas
        tablas_relacionadas = ['pagos', 'prestamos', 'clientes', 'amortizaciones']
        print(f"\n📋 Verificando tablas relacionadas:")
        for tabla in tablas_relacionadas:
            if tabla in tablas:
                try:
                    resultado = db.execute(text(f"SELECT COUNT(*) FROM {tabla}"))
                    count = resultado.scalar()
                    print(f"   ✅ {tabla}: EXISTE ({count} registros)")
                except Exception as e:
                    print(f"   ⚠️  {tabla}: EXISTE pero error al contar: {e}")
            else:
                print(f"   ❌ {tabla}: NO EXISTE")
        
        print("\n" + "=" * 80)
        print("3. VERIFICACIÓN DE ESQUEMAS")
        print("=" * 80)
        
        # Verificar esquemas disponibles
        try:
            resultado = db.execute(text("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
                ORDER BY schema_name
            """))
            esquemas = [row[0] for row in resultado.fetchall()]
            print(f"\n📁 Esquemas disponibles: {', '.join(esquemas)}")
            
            # Verificar en qué esquema está pagos_staging
            if "pagos_staging" in tablas:
                resultado = db.execute(text("""
                    SELECT table_schema, table_name 
                    FROM information_schema.tables 
                    WHERE table_name = 'pagos_staging'
                """))
                esquema_info = resultado.fetchall()
                if esquema_info:
                    print(f"\n📁 Ubicación de pagos_staging:")
                    for schema, table in esquema_info:
                        print(f"   - {schema}.{table}")
        except Exception as e:
            print(f"⚠️  Error al verificar esquemas: {e}")
        
        print("\n" + "=" * 80)
        print("4. VERIFICACIÓN DE CONSULTAS SQL")
        print("=" * 80)
        
        # Intentar consulta SQL directa a pagos_staging
        if "pagos_staging" in tablas:
            try:
                resultado = db.execute(text("SELECT COUNT(*) FROM pagos_staging"))
                count = resultado.scalar()
                print(f"✅ Consulta SQL directa a pagos_staging: OK ({count} registros)")
            except Exception as e:
                print(f"❌ Error en consulta SQL a pagos_staging: {e}")
        else:
            print("⚠️  No se puede probar consulta SQL: tabla pagos_staging no existe")
        
        db.close()
        
        print("\n" + "=" * 80)
        if "pagos_staging" in tablas:
            print("✅ VERIFICACIÓN COMPLETA: La conexión está correcta y pagos_staging existe")
        else:
            print("❌ VERIFICACIÓN COMPLETA: La conexión funciona pero pagos_staging NO existe")
            print("   Acción requerida: Crear la tabla pagos_staging o verificar conexión a BD correcta")
        print("=" * 80)
        
        return "pagos_staging" in tablas
        
    except Exception as e:
        print(f"\n❌ ERROR DE CONEXIÓN: {e}")
        print(f"   Tipo de error: {type(e).__name__}")
        import traceback
        print(f"\n   Traceback completo:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = verificar_conexion()
    sys.exit(0 if success else 1)

