#!/usr/bin/env python3
"""
Script para corregir docstrings malformados en archivos Python
"""

import re
import os
from pathlib import Path

def fix_docstrings_in_file(file_path):
    """Corrige docstrings malformados en un archivo"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Patrón para encontrar docstrings malformados con caracteres especiales
        pattern = r'""""""\s*\n\s*([^"]*[^\s][^"]*)\n\s*""""""'
        
        def replace_docstring(match):
            docstring_content = match.group(1).strip()
            # Convertir a comentario simple
            return f"    # {docstring_content}"
        
        # Reemplazar docstrings malformados
        new_content = re.sub(pattern, replace_docstring, content, flags=re.MULTILINE)
        
        # Si hubo cambios, escribir el archivo
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Corregido: {file_path}")
            return True
        else:
            print(f"Sin cambios: {file_path}")
            return False
            
    except Exception as e:
        print(f"Error procesando {file_path}: {e}")
        return False

def main():
    """Función principal"""
    # Archivos específicos que sabemos que tienen problemas
    files_to_fix = [
        "backend/app/api/v1/endpoints/amortizacion.py",
        "backend/app/api/v1/endpoints/pagos.py",
        "backend/app/api/v1/endpoints/concesionarios.py",
        "backend/app/api/v1/endpoints/clientes.py",
        "backend/app/api/v1/endpoints/conciliacion_bancaria.py"
    ]
    
    fixed_count = 0
    for file_path in files_to_fix:
        if os.path.exists(file_path):
            if fix_docstrings_in_file(file_path):
                fixed_count += 1
    
    print(f"\nTotal de archivos corregidos: {fixed_count}")

if __name__ == "__main__":
    main()
