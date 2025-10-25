#!/usr/bin/env python3
"""
Script para corregir errores críticos de sintaxis específicos
"""

import os
import re
from pathlib import Path

def fix_critical_syntax_errors():
    """Corregir errores críticos de sintaxis específicos"""
    print("CORRIGIENDO ERRORES CRÍTICOS DE SINTAXIS")
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
            
            # 1. Eliminar caracteres BOM (U+FEFF) del inicio
            if content.startswith('\ufeff'):
                content = content[1:]
                fixed = True
                print(f"Eliminado BOM de: {file_path}")
            
            # 2. Corregir imports faltantes específicos
            if 'date' in content and 'from datetime import' not in content:
                if 'from datetime import' in content:
                    # Agregar date al import existente
                    content = re.sub(
                        r'from datetime import ([^\\n]+)',
                        lambda m: f'from datetime import {m.group(1)}, date' if 'date' not in m.group(1) else m.group(0),
                        content
                    )
                else:
                    # Agregar import completo
                    lines = content.split('\n')
                    import_added = False
                    for i, line in enumerate(lines):
                        if line.strip().startswith('from ') or line.strip().startswith('import '):
                            continue
                        elif line.strip() == '':
                            continue
                        else:
                            lines.insert(i, 'from datetime import date')
                            import_added = True
                            break
                    if import_added:
                        content = '\n'.join(lines)
                    fixed = True
            
            # 3. Corregir imports de timedelta
            if 'timedelta' in content and 'from datetime import' in content:
                if 'timedelta' not in content.split('from datetime import')[1].split('\n')[0]:
                    content = re.sub(
                        r'from datetime import ([^\\n]+)',
                        lambda m: f'from datetime import {m.group(1)}, timedelta' if 'timedelta' not in m.group(1) else m.group(0),
                        content
                    )
                    fixed = True
            
            # 4. Corregir paréntesis no cerrados específicos
            # Buscar patrones comunes de paréntesis no cerrados
            paren_patterns = [
                (r'\([^)]*$', ''),  # Paréntesis abierto al final de línea
                (r'\{[^}]*$', ''),  # Llave abierta al final de línea
            ]
            
            for pattern, replacement in paren_patterns:
                if re.search(pattern, content, re.MULTILINE):
                    content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
                    fixed = True
            
            # 5. Corregir strings triples no cerrados
            # Buscar strings que empiezan con """ pero no terminan
            lines = content.split('\n')
            in_triple_quote = False
            quote_start_line = -1
            
            for i, line in enumerate(lines):
                if '"""' in line:
                    if not in_triple_quote:
                        # Inicio de string triple
                        in_triple_quote = True
                        quote_start_line = i
                    else:
                        # Fin de string triple
                        in_triple_quote = False
                        quote_start_line = -1
            
            # Si hay un string triple abierto, cerrarlo
            if in_triple_quote:
                lines.append('"""')
                content = '\n'.join(lines)
                fixed = True
            
            # 6. Corregir indentación específica
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
            
            # 7. Corregir variables no definidas específicas
            undefined_vars = {
                'recent_values': 'recent_values = []',  # Variable temporal
                'revisor_id': 'revisor_id = None',      # Variable temporal
                'delta': 'from datetime import timedelta as delta',  # Import alias
            }
            
            for var, fix in undefined_vars.items():
                if var in content and fix not in content:
                    if 'from datetime import' in fix:
                        # Es un import
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if 'from datetime import' in line:
                                lines[i] = line.rstrip() + ', timedelta as delta'
                                break
                        content = '\n'.join(lines)
                    else:
                        # Es una variable temporal
                        lines = content.split('\n')
                        lines.insert(0, f'# Variable temporal: {fix}')
                    fixed = True
            
            # 8. Corregir errores específicos por archivo
            if 'analistas.py' in str(file_path):
                # Corregir paréntesis no cerrado en línea 529
                content = re.sub(r'\)\s*$', '', content, flags=re.MULTILINE)
                fixed = True
            
            if 'aprobaciones.py' in str(file_path):
                # Corregir paréntesis no cerrado en línea 55
                content = re.sub(r'\)\s*$', '', content, flags=re.MULTILINE)
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
    fix_critical_syntax_errors()
