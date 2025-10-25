#!/usr/bin/env python3
"""
Script para corregir errores fáciles automáticamente
"""

import os
import re
from pathlib import Path

def fix_easy_errors():
    """Corregir errores fáciles automáticamente"""
    print("CORRIGIENDO ERRORES FÁCILES AUTOMÁTICAMENTE")
    print("=" * 50)
    
    backend_path = Path("backend")
    python_files = list(backend_path.rglob("*.py"))
    
    total_fixed = 0
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            fixed = False
            
            # 1. Corregir imports incompletos
            # Patrón: "from module import " (sin nombres)
            if re.search(r'from\s+\w+\s+import\s*$', content, re.MULTILINE):
                content = re.sub(r'from\s+(\w+)\s+import\s*$', r'# from \1 import  # TODO: Agregar imports específicos', content, flags=re.MULTILINE)
                fixed = True
            
            # 2. Eliminar líneas con solo paréntesis sueltos
            lines = content.split('\n')
            new_lines = []
            for line in lines:
                stripped = line.strip()
                # Eliminar líneas que solo contienen paréntesis sueltos
                if stripped in ['(', ')', '{', '}', '[', ']', '):', '),', ');', '): ', '), ', '); ']:
                    continue
                new_lines.append(line)
            
            if len(new_lines) != len(lines):
                content = '\n'.join(new_lines)
                fixed = True
            
            # 3. Corregir strings triples no cerrados simples
            if '"""' in content:
                triple_quotes = content.count('"""')
                if triple_quotes % 2 != 0:
                    # Hay un string triple no cerrado, cerrarlo al final
                    content += '\n"""'
                    fixed = True
            
            # 4. Corregir corchetes no cerrados simples
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.strip().startswith('[') and not line.strip().endswith(']') and '=' in line:
                    lines[i] = line.strip() + ']'
                    fixed = True
            content = '\n'.join(lines)
            
            # 5. Corregir indentación básica
            lines = content.split('\n')
            for i, line in enumerate(lines):
                # Corregir líneas que tienen indentación incorrecta después de if/else/try
                if re.match(r'^\s*(if|else|try|except|for|while|def|class)\s+.*:', line):
                    # Verificar si la siguiente línea está mal indentada
                    if i + 1 < len(lines):
                        next_line = lines[i + 1]
                        if next_line.strip() and not next_line.startswith('    ') and not next_line.startswith('\t'):
                            # Agregar indentación correcta
                            lines[i + 1] = '    ' + next_line.strip()
                            fixed = True
            content = '\n'.join(lines)
            
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
    fix_easy_errors()
