#!/usr/bin/env python3
"""
Script específico para eliminar caracteres BOM y corregir errores simples
"""

import os
from pathlib import Path

def remove_bom_and_fix_simple():
    """Eliminar caracteres BOM y corregir errores simples"""
    print("ELIMINANDO CARACTERES BOM Y CORRIGIENDO ERRORES SIMPLES")
    print("=" * 60)
    
    backend_path = Path("backend")
    python_files = list(backend_path.rglob("*.py"))
    
    total_fixed = 0
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            fixed = False
            
            # 1. Eliminar caracteres BOM (U+FEFF) del inicio
            if content.startswith('\ufeff'):
                content = content[1:]
                fixed = True
                print(f"Eliminado BOM de: {file_path}")
            
            # 2. Eliminar líneas que solo contienen paréntesis sueltos
            lines = content.split('\n')
            new_lines = []
            for line in lines:
                stripped = line.strip()
                # Eliminar líneas que solo contienen paréntesis sueltos
                if stripped in ['(', ')', '{', '}', '[', ']']:
                    continue
                # Eliminar líneas que solo contienen paréntesis con espacios
                if stripped in ['( ', ' )', '{ ', ' }', '[ ', ' ]']:
                    continue
                new_lines.append(line)
            
            if len(new_lines) != len(lines):
                content = '\n'.join(new_lines)
                fixed = True
            
            # 3. Corregir strings triples no cerrados simples
            # Buscar strings que empiezan con """ pero no terminan en el mismo archivo
            if '"""' in content:
                # Contar triple quotes
                triple_quotes = content.count('"""')
                if triple_quotes % 2 != 0:
                    # Hay un string triple no cerrado, cerrarlo al final
                    content += '\n"""'
                    fixed = True
            
            # Guardar archivo si hubo cambios
            if fixed:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                total_fixed += 1
                print(f"Corregido: {file_path}")
        
        except Exception as e:
            print(f"Error corrigiendo {file_path}: {e}")
    
    print(f"\nArchivos corregidos: {total_fixed}")
    return total_fixed

if __name__ == "__main__":
    remove_bom_and_fix_simple()
