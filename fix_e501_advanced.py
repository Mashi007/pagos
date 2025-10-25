#!/usr/bin/env python3
"""
Script avanzado para corregir errores E501 (línea demasiado larga)
Maneja casos más complejos que el script anterior
"""

import os
import re
import sys
from pathlib import Path

def fix_long_line(line, max_length=79):
    """Corrige una línea larga usando diferentes estrategias"""
    original_line = line
    line = line.rstrip()
    
    # Si ya está dentro del límite, no hacer nada
    if len(line) <= max_length:
        return line
    
    # Estrategia 1: Dividir en operadores binarios
    if any(op in line for op in [' and ', ' or ', ' + ', ' - ', ' * ', ' / ', ' == ', ' != ', ' <= ', ' >= ']):
        # Buscar el último operador antes del límite
        for op in [' and ', ' or ', ' + ', ' - ', ' * ', ' / ', ' == ', ' != ', ' <= ', ' >= ']:
            if op in line:
                parts = line.split(op)
                if len(parts) > 1:
                    # Intentar dividir en el último operador
                    for i in range(len(parts) - 1, 0, -1):
                        left_part = op.join(parts[:i])
                        right_part = op.join(parts[i:])
                        if len(left_part) <= max_length - 4:  # 4 para "op "
                            return f"{left_part}{op}\n    {right_part}"
    
    # Estrategia 2: Dividir en comas (para argumentos de función)
    if ',' in line and '(' in line:
        # Buscar la última coma antes del límite
        comma_pos = line.rfind(',', 0, max_length - 4)
        if comma_pos > 0:
            left_part = line[:comma_pos + 1]
            right_part = line[comma_pos + 1:].lstrip()
            return f"{left_part}\n    {right_part}"
    
    # Estrategia 3: Dividir en paréntesis
    if '(' in line and ')' in line:
        paren_pos = line.find('(')
        if paren_pos > 0 and paren_pos < max_length - 4:
            left_part = line[:paren_pos]
            right_part = line[paren_pos:]
            return f"{left_part}\n    {right_part}"
    
    # Estrategia 4: Dividir en strings largos
    if 'f"' in line or "f'" in line:
        # Buscar strings f largos
        f_string_pattern = r'f["\']([^"\']*)["\']'
        matches = list(re.finditer(f_string_pattern, line))
        for match in matches:
            if len(match.group()) > max_length - 20:  # Margen para el resto de la línea
                start, end = match.span()
                before = line[:start]
                after = line[end:]
                f_content = match.group(1)
                
                # Dividir el contenido del f-string
                if len(f_content) > 50:
                    mid_point = len(f_content) // 2
                    # Buscar un punto de división natural
                    for i in range(mid_point, len(f_content)):
                        if f_content[i] in ' .':
                            f_content1 = f_content[:i+1]
                            f_content2 = f_content[i+1:]
                            return f"{before}f\"{f_content1}\"\n    f\"{f_content2}\"{after}"
    
    # Estrategia 5: Dividir en comentarios largos
    if line.strip().startswith('#'):
        if len(line) > max_length:
            # Dividir el comentario
            comment_content = line.strip()[1:].strip()
            if len(comment_content) > max_length - 4:
                mid_point = len(comment_content) // 2
                # Buscar un punto de división natural
                for i in range(mid_point, len(comment_content)):
                    if comment_content[i] in ' .':
                        part1 = comment_content[:i+1]
                        part2 = comment_content[i+1:]
                        return f"# {part1}\n# {part2}"
    
    # Estrategia 6: Dividir en asignaciones largas
    if ' = ' in line:
        equal_pos = line.find(' = ')
        if equal_pos > 0 and equal_pos < max_length - 4:
            left_part = line[:equal_pos + 3]
            right_part = line[equal_pos + 3:].lstrip()
            return f"{left_part}\n    {right_part}"
    
    # Estrategia 7: Dividir en el último espacio antes del límite
    last_space = line.rfind(' ', 0, max_length - 4)
    if last_space > 0:
        left_part = line[:last_space]
        right_part = line[last_space + 1:]
        return f"{left_part}\n    {right_part}"
    
    # Si no se puede dividir de manera inteligente, dividir por caracteres
    if len(line) > max_length:
        return f"{line[:max_length-3]}\n    {line[max_length-3:]}"
    
    return original_line

def process_file(file_path):
    """Procesa un archivo para corregir errores E501"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        modified = False
        new_lines = []
        
        for i, line in enumerate(lines):
            original_line = line
            new_line = fix_long_line(line)
            
            if new_line != original_line:
                modified = True
                # Si la línea se dividió en múltiples líneas
                if '\n' in new_line:
                    split_lines = new_line.split('\n')
                    new_lines.extend(split_lines)
                    # Asegurar que todas las líneas divididas terminen con \n
                    for j in range(len(split_lines) - 1):
                        if not split_lines[j].endswith('\n'):
                            split_lines[j] += '\n'
                else:
                    new_lines.append(new_line)
            else:
                new_lines.append(line)
        
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            return True
        
        return False
    
    except Exception as e:
        print(f"Error procesando {file_path}: {e}")
        return False

def main():
    """Función principal"""
    backend_dir = Path("backend/app")
    
    if not backend_dir.exists():
        print("Error: No se encontró el directorio backend/app")
        return
    
    # Obtener todos los archivos Python
    python_files = list(backend_dir.rglob("*.py"))
    
    print(f"Procesando {len(python_files)} archivos Python...")
    
    modified_files = []
    
    for file_path in python_files:
        if process_file(file_path):
            modified_files.append(str(file_path))
            print(f"Modificado: {file_path}")
    
    print(f"\nArchivos modificados: {len(modified_files)}")
    for file_path in modified_files:
        print(f"  - {file_path}")

if __name__ == "__main__":
    main()