#!/usr/bin/env python3
"""
Script para reemplazar todas las referencias a roles antiguos
"""
import os
import re

# Directorio base
BASE_DIR = "c:\\Users\\PORTATIL\\Documents\\GitHub\\pagos\\backend\\app\\api"

# Reemplazos a realizar
REPLACEMENTS = [
    (r'"ADMIN"', '"ADMINISTRADOR_GENERAL"'),
    (r"'ADMIN'", "'ADMINISTRADOR_GENERAL'"),
    (r'User\.rol == "ADMIN"', 'User.rol == "ADMINISTRADOR_GENERAL"'),
    (r"User\.rol == 'ADMIN'", "User.rol == 'ADMINISTRADOR_GENERAL'"),
]

def replace_in_file(filepath):
    """Reemplazar en un archivo"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        for pattern, replacement in REPLACEMENTS:
            content = re.sub(pattern, replacement, content)
        
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Actualizado: {filepath}")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"Error en {filepath}: {e}")
        return False

def main():
    """Función principal"""
    print("\nREEMPLAZANDO REFERENCIAS A ROLES ANTIGUOS\n")
    
    files_updated = 0
    
    for root, dirs, files in os.walk(BASE_DIR):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                if replace_in_file(filepath):
                    files_updated += 1
    
    print(f"\nTotal archivos actualizados: {files_updated}\n")

if __name__ == "__main__":
    main()

