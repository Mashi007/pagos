#!/usr/bin/env python3
"""
Script para arreglar archivos que usan logger sin importarlo
"""

import os
import re
import glob

def fix_logger_imports():
    """Arreglar imports de logger en archivos Python"""
    
    # Buscar todos los archivos Python en backend/app
    python_files = glob.glob("backend/app/**/*.py", recursive=True)
    
    fixed_files = []
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Verificar si el archivo usa logger pero no lo importa
            uses_logger = re.search(r'\blogger\.', content)
            has_logger_import = re.search(r'import logging|from logging import|logger = logging\.getLogger', content)
            
            if uses_logger and not has_logger_import:
                print(f"Arreglando: {file_path}")
                
                # Encontrar la primera línea que no sea comentario o import
                lines = content.split('\n')
                insert_index = 0
                
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    if stripped and not stripped.startswith('#') and not stripped.startswith('"""') and not stripped.startswith("'''"):
                        # Buscar imports existentes
                        if stripped.startswith('import ') or stripped.startswith('from '):
                            insert_index = i + 1
                        else:
                            break
                
                # Insertar import de logging
                lines.insert(insert_index, 'import logging')
                lines.insert(insert_index + 1, '')
                lines.insert(insert_index + 2, 'logger = logging.getLogger(__name__)')
                
                # Escribir archivo corregido
                new_content = '\n'.join(lines)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                fixed_files.append(file_path)
                
        except Exception as e:
            print(f"Error procesando {file_path}: {e}")
    
    return fixed_files

if __name__ == "__main__":
    print("ARREGLANDO IMPORTS DE LOGGER")
    print("=" * 50)
    
    fixed_files = fix_logger_imports()
    
    print(f"\nRESUMEN:")
    print(f"Archivos corregidos: {len(fixed_files)}")
    
    if fixed_files:
        print("\nArchivos corregidos:")
        for file_path in fixed_files:
            print(f"   - {file_path}")
    
    print("\nCorreccion completada")
