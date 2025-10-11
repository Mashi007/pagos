#!/usr/bin/env python3
"""
Script para corregir importaciones de app.config a app.core.config
"""
import os
import re
from pathlib import Path

def find_python_files(directory):
    """Encuentra todos los archivos .py en el directorio"""
    return list(Path(directory).rglob("*.py"))

def check_file(filepath):
    """Verifica si un archivo tiene la importación incorrecta"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            return 'from app.config import' in content
    except Exception as e:
        print(f"⚠️  Error leyendo {filepath}: {e}")
        return False

def fix_file(filepath):
    """Corrige las importaciones en un archivo"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Realizar el reemplazo
        new_content = re.sub(
            r'from app\.config import',
            'from app.core.config import',
            content
        )
        
        if content != new_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
        return False
    except Exception as e:
        print(f"❌ Error corrigiendo {filepath}: {e}")
        return False

def main():
    # Directorio base del proyecto
    base_dir = Path("backend/app")
    
    if not base_dir.exists():
        print(f"❌ Error: No se encontró el directorio {base_dir}")
        print("   Ejecuta este script desde la raíz del proyecto")
        return
    
    print("🔧 Corrigiendo importaciones de config en todo el proyecto...")
    print("")
    
    # Buscar archivos afectados
    python_files = find_python_files(base_dir)
    affected_files = [f for f in python_files if check_file(f)]
    
    if not affected_files:
        print("✅ No se encontraron archivos con importaciones incorrectas")
        return
    
    print(f"📋 Archivos que necesitan corrección ({len(affected_files)}):")
    for f in affected_files:
        print(f"   - {f}")
    print("")
    
    # Confirmar
    confirm = input("¿Deseas corregir estos archivos? (s/n): ").strip().lower()
    
    if confirm not in ['s', 'si', 'sí', 'y', 'yes']:
        print("❌ Operación cancelada")
        return
    
    # Aplicar correcciones
    print("")
    print("🔄 Aplicando correcciones...")
    fixed_count = 0
    
    for filepath in affected_files:
        if fix_file(filepath):
            print(f"   ✅ {filepath}")
            fixed_count += 1
        else:
            print(f"   ⚠️  {filepath} (sin cambios)")
    
    print("")
    print(f"✅ Correcciones aplicadas: {fixed_count}/{len(affected_files)} archivos")
    
    # Verificar
    print("")
    print("🔍 Verificando correcciones...")
    remaining = [f for f in python_files if check_file(f)]
    
    if not remaining:
        print("✅ Todas las importaciones fueron corregidas exitosamente")
    else:
        print(f"⚠️  Aún quedan {len(remaining)} archivo(s) con importaciones incorrectas:")
        for f in remaining:
            print(f"   - {f}")
    
    print("")
    print("🎯 Resumen de cambios realizados:")
    print("   - Cambiado: from app.config import → from app.core.config import")
    print("")
    print("📝 Próximos pasos:")
    print("   1. Revisar los cambios con: git diff")
    print("   2. Hacer commit de los cambios")
    print("   3. Reiniciar el servidor")

if __name__ == "__main__":
    main()
