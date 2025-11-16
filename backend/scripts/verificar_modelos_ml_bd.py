#!/usr/bin/env python3
"""
Script para verificar si las tablas de modelos ML están conectadas a la base de datos
"""

import sys
from pathlib import Path

# Agregar el directorio backend al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, inspect, text
from app.core.config import settings

def verificar_tablas_modelos_ml():
    """Verificar si las tablas de modelos ML existen en la base de datos"""
    try:
        print("🔍 Verificando conexión a base de datos y tablas de modelos ML...")
        print(f"📊 Conectando a: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'BD local'}")
        
        engine = create_engine(settings.DATABASE_URL)
        inspector = inspect(engine)
        
        tablas_requeridas = [
            ('modelos_riesgo', 'Modelos de Riesgo ML'),
            ('modelos_impago_cuotas', 'Modelos de Impago de Cuotas ML'),
        ]
        
        tablas_existentes = inspector.get_table_names()
        
        print("\n📋 Estado de las tablas de modelos ML:")
        print("=" * 70)
        
        todas_existen = True
        for tabla, nombre in tablas_requeridas:
            existe = tabla in tablas_existentes
            estado = "✅ EXISTE" if existe else "❌ NO EXISTE"
            print(f"  {tabla:<35} {nombre:<30} {estado}")
            if not existe:
                todas_existen = False
        
        print("=" * 70)
        
        # Si las tablas existen, verificar estructura
        if todas_existen:
            print("\n🔍 Verificando estructura de las tablas...")
            print("-" * 70)
            
            for tabla, nombre in tablas_requeridas:
                try:
                    columnas = inspector.get_columns(tabla)
                    indices = inspector.get_indexes(tabla)
                    print(f"\n  📊 {tabla} ({nombre}):")
                    print(f"     - Columnas: {len(columnas)}")
                    print(f"     - Índices: {len(indices)}")
                    
                    # Verificar columnas críticas
                    nombres_columnas = [col['name'] for col in columnas]
                    columnas_criticas = ['id', 'nombre', 'algoritmo', 'activo', 'ruta_archivo']
                    faltantes = [col for col in columnas_criticas if col not in nombres_columnas]
                    
                    if faltantes:
                        print(f"     ⚠️  Columnas críticas faltantes: {', '.join(faltantes)}")
                    else:
                        print(f"     ✅ Todas las columnas críticas existen")
                        
                except Exception as e:
                    print(f"     ❌ Error verificando estructura: {e}")
        
        # Verificar estado de Alembic
        print("\n🔄 Verificando estado de migraciones Alembic...")
        print("-" * 70)
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT version_num FROM alembic_version"))
                version_actual = result.scalar()
                print(f"  Versión actual de Alembic: {version_actual}")
                
                # Verificar migraciones específicas
                migraciones_ml = [
                    '20251114_04_modelos_riesgo',
                    '20251114_05_modelos_impago_cuotas',
                ]
                
                print("\n  Migraciones de modelos ML:")
                for migracion in migraciones_ml:
                    # Verificar si la migración está aplicada (esto requiere revisar el historial)
                    print(f"    - {migracion}")
                    
        except Exception as e:
            print(f"  ⚠️  No se pudo verificar estado de Alembic: {e}")
        
        # Resumen
        print("\n" + "=" * 70)
        if todas_existen:
            print("✅ RESULTADO: Todas las tablas de modelos ML están conectadas a la BD")
            print("\n💡 Próximos pasos:")
            print("   1. Verificar que scikit-learn esté instalado")
            print("   2. Probar entrenar un modelo")
        else:
            print("❌ RESULTADO: Algunas tablas de modelos ML NO están conectadas a la BD")
            print("\n💡 Solución:")
            print("   Ejecuta las migraciones:")
            print("   cd backend")
            print("   alembic upgrade head")
        print("=" * 70)
        
        return todas_existen
        
    except Exception as e:
        print(f"\n❌ ERROR: No se pudo conectar a la base de datos: {e}")
        print("\n💡 Verifica:")
        print("   1. Que DATABASE_URL esté configurado correctamente")
        print("   2. Que la base de datos esté accesible")
        print("   3. Que las credenciales sean correctas")
        return False

if __name__ == "__main__":
    verificar_tablas_modelos_ml()

