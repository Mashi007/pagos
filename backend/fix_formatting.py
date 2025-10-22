#!/usr/bin/env python3
"""
Script para aplicar correcciones de formato automáticamente
Simula el comportamiento de black para corregir problemas comunes de linting
"""
import os
import re
import glob
from pathlib import Path

def fix_python_file(file_path):
    """Aplica correcciones de formato a un archivo Python"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 1. Corregir líneas largas dividiendo parámetros de funciones
        content = re.sub(
            r'(\w+): (\w+) = Field\(([^)]{80,})\)',
            lambda m: f"{m.group(1)}: {m.group(2)} = Field(\n    {m.group(3)}\n)",
            content
        )
        
        # 2. Agregar líneas en blanco entre clases y funciones
        content = re.sub(r'(\n    return [^\n]+\n)(def |class |@)', r'\1\n\2', content)
        content = re.sub(r'(\n    model_config = ConfigDict[^\n]+\n)(def |class |@)', r'\1\n\2', content)
        
        # 3. Corregir comparaciones booleanas
        content = re.sub(r'(\w+) == True\b', r'\1 is True', content)
        content = re.sub(r'(\w+) == False\b', r'\1 is False', content)
        content = re.sub(r'(\w+) != True\b', r'\1 is not True', content)
        content = re.sub(r'(\w+) != False\b', r'\1 is not False', content)
        
        # 4. Eliminar espacios en blanco al final de líneas
        content = re.sub(r'[ \t]+$', '', content, flags=re.MULTILINE)
        
        # 5. Agregar línea en blanco al final del archivo si no existe
        if content and not content.endswith('\n'):
            content += '\n'
        
        # Solo escribir si hubo cambios
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Corregido: {file_path}")
            return True
        else:
            print(f"⚪ Sin cambios: {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error en {file_path}: {e}")
        return False

def main():
    """Procesa todos los archivos Python en el directorio app/"""
    app_dir = Path("app")
    if not app_dir.exists():
        print("❌ Directorio app/ no encontrado")
        return
    
    # Buscar todos los archivos Python
    python_files = list(app_dir.rglob("*.py"))
    
    print(f"🔍 Encontrados {len(python_files)} archivos Python")
    
    corrected_count = 0
    for file_path in python_files:
        if fix_python_file(file_path):
            corrected_count += 1
    
    print(f"\n📊 Resumen:")
    print(f"   Total archivos: {len(python_files)}")
    print(f"   Archivos corregidos: {corrected_count}")
    print(f"   Archivos sin cambios: {len(python_files) - corrected_count}")

if __name__ == "__main__":
    main()
