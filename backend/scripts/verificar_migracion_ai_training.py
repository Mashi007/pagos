#!/usr/bin/env python3
"""
Script para verificar si la migración de AI training ya se aplicó
"""

import sys
from pathlib import Path

# Agregar el directorio backend al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, inspect, text
from app.core.config import settings

def verificar_tablas_ai_training():
    """Verificar si las tablas de AI training existen"""
    try:
        print("🔍 Verificando tablas de AI training...")
        print(f"📊 Conectando a: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'BD local'}")
        
        engine = create_engine(settings.DATABASE_URL)
        inspector = inspect(engine)
        
        tablas_requeridas = [
            'conversaciones_ai',
            'fine_tuning_jobs',
            'documento_ai_embeddings',
            'modelos_riesgo'
        ]
        
        tablas_existentes = inspector.get_table_names()
        
        print("\n📋 Estado de las tablas:")
        print("-" * 60)
        
        todas_existen = True
        for tabla in tablas_requeridas:
            existe = tabla in tablas_existentes
            estado = "✅ EXISTE" if existe else "❌ NO EXISTE"
            print(f"  {tabla:<35} {estado}")
            if not existe:
                todas_existen = False
        
        print("-" * 60)
        
        # Verificar estado de Alembic
        print("\n🔄 Verificando estado de migraciones Alembic...")
        with engine.connect() as conn:
            try:
                result = conn.execute(text("SELECT version_num FROM alembic_version"))
                version_actual = result.scalar()
                print(f"  Versión actual: {version_actual}")
                
                # Verificar si la migración específica está aplicada
                if version_actual == '20250114_ai_training':
                    print("  ✅ Migración 20250114_ai_training está aplicada")
                else:
                    print(f"  ⚠️ Versión actual es diferente: {version_actual}")
                    print("  ℹ️ Verificar si la migración está en el historial")
            except Exception as e:
                print(f"  ⚠️ Error verificando versión: {e}")
        
        return todas_existen
        
    except Exception as e:
        print(f"❌ Error verificando tablas: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🔍 VERIFICACIÓN DE MIGRACIÓN AI TRAINING")
    print("=" * 60)
    
    tablas_existen = verificar_tablas_ai_training()
    
    print("\n" + "=" * 60)
    print("📊 RESUMEN")
    print("=" * 60)
    
    if tablas_existen:
        print("✅ Todas las tablas de AI training existen")
        print("   → La migración YA SE APLICÓ")
        print("\n💡 RECOMENDACIÓN:")
        print("   - Mantener la migración actual")
        print("   - Para futuras migraciones, considerar dividirlas")
    else:
        print("❌ Algunas tablas de AI training NO existen")
        print("   → La migración NO SE HA APLICADO")
        print("\n💡 RECOMENDACIÓN:")
        print("   - Implementar Opción 1: Dividir en 4 migraciones")
        print("   - Crear migraciones separadas por tabla")
    
    print("=" * 60)
    
    sys.exit(0 if tablas_existen else 1)

