#!/usr/bin/env python3
"""
Script para verificar si la tabla documentos_ai existe en la base de datos
"""

import sys
import os
from pathlib import Path

# Agregar el directorio del proyecto al path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text, inspect
from app.core.config import settings

def verificar_tabla_documentos_ai():
    """Verifica si la tabla documentos_ai existe en la base de datos"""
    try:
        print("🔍 Verificando conexión a la base de datos...")
        engine = create_engine(settings.DATABASE_URL)
        
        with engine.connect() as conn:
            # Verificar conexión
            conn.execute(text("SELECT 1"))
            print("✅ Conexión a la base de datos exitosa")
            
            # Obtener inspector para verificar tablas
            inspector = inspect(engine)
            tablas = inspector.get_table_names()
            
            print(f"\n📊 Total de tablas en la base de datos: {len(tablas)}")
            
            # Verificar si existe la tabla documentos_ai
            if "documentos_ai" in tablas:
                print("✅ La tabla 'documentos_ai' EXISTE")
                
                # Obtener información de la tabla
                columnas = inspector.get_columns("documentos_ai")
                print(f"\n📋 Columnas en la tabla 'documentos_ai':")
                for col in columnas:
                    tipo = col['type']
                    nullable = "NULL" if col['nullable'] else "NOT NULL"
                    default = f" DEFAULT {col['default']}" if col.get('default') else ""
                    print(f"   - {col['name']}: {tipo} {nullable}{default}")
                
                # Obtener índices
                indices = inspector.get_indexes("documentos_ai")
                if indices:
                    print(f"\n🔍 Índices en la tabla 'documentos_ai':")
                    for idx in indices:
                        columnas_idx = ', '.join(idx['column_names'])
                        unico = "UNIQUE" if idx.get('unique') else ""
                        print(f"   - {idx['name']}: {columnas_idx} {unico}")
                
                # Contar registros
                result = conn.execute(text("SELECT COUNT(*) FROM documentos_ai"))
                count = result.scalar()
                print(f"\n📊 Total de documentos en la tabla: {count}")
                
                return True
            else:
                print("❌ La tabla 'documentos_ai' NO EXISTE")
                print("\n📝 Tablas disponibles (primeras 20):")
                for tabla in sorted(tablas)[:20]:
                    print(f"   - {tabla}")
                if len(tablas) > 20:
                    print(f"   ... y {len(tablas) - 20} más")
                
                return False
                
    except Exception as e:
        print(f"❌ Error verificando tabla: {e}")
        import traceback
        traceback.print_exc()
        return False

def verificar_migraciones():
    """Verifica el estado de las migraciones de Alembic"""
    try:
        print("\n🔄 Verificando estado de migraciones de Alembic...")
        
        from alembic import command
        from alembic.config import Config
        from pathlib import Path
        
        alembic_ini_path = Path(__file__).parent.parent / "alembic.ini"
        
        if not alembic_ini_path.exists():
            print("⚠️ alembic.ini no encontrado")
            return False
        
        alembic_cfg = Config(str(alembic_ini_path))
        alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
        
        # Obtener versión actual
        from alembic.script import ScriptDirectory
        script = ScriptDirectory.from_config(alembic_cfg)
        
        # Conectar a la BD para verificar versión
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            # Verificar si existe la tabla alembic_version
            inspector = inspect(engine)
            if "alembic_version" in inspector.get_table_names():
                result = conn.execute(text("SELECT version_num FROM alembic_version"))
                version_actual = result.scalar()
                print(f"✅ Versión actual de Alembic: {version_actual}")
                
                # Verificar si existe la migración de documentos_ai
                head_revision = script.get_current_head()
                print(f"📌 Head de migraciones: {head_revision}")
                
                # Buscar la migración de documentos_ai
                for script_obj in script.walk_revisions():
                    if "documentos_ai" in script_obj.revision.lower() or "documentos_ai" in str(script_obj.path).lower():
                        print(f"✅ Migración de documentos_ai encontrada: {script_obj.revision}")
                        return True
                
                print("⚠️ Migración de documentos_ai no encontrada en el historial")
                return False
            else:
                print("⚠️ Tabla alembic_version no existe - las migraciones no se han ejecutado")
                return False
                
    except Exception as e:
        print(f"❌ Error verificando migraciones: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🔍 VERIFICACIÓN DE TABLA documentos_ai")
    print("=" * 60)
    
    tabla_existe = verificar_tabla_documentos_ai()
    migraciones_ok = verificar_migraciones()
    
    print("\n" + "=" * 60)
    print("📊 RESUMEN")
    print("=" * 60)
    print(f"Tabla documentos_ai existe: {'✅ SÍ' if tabla_existe else '❌ NO'}")
    print(f"Migraciones verificadas: {'✅ OK' if migraciones_ok else '⚠️ REVISAR'}")
    
    if not tabla_existe:
        print("\n💡 RECOMENDACIONES:")
        print("   1. Ejecutar: cd backend && alembic upgrade head")
        print("   2. Verificar que la migración 20251114_create_documentos_ai esté aplicada")
        print("   3. Revisar los logs del servidor para ver si hay errores de migración")
    
    sys.exit(0 if tabla_existe else 1)

