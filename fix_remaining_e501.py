#!/usr/bin/env python3
"""
Script para corregir automáticamente los errores E501 restantes
"""

import os
import re
import subprocess
import sys

def get_e501_errors():
    """Obtener lista de errores E501"""
    try:
        result = subprocess.run(
            ["py", "-m", "flake8", "backend/app/", "--count", "--select=E501"],
            capture_output=True,
            text=True,
            cwd="."
        )
        
        if result.returncode == 0:
            return []
        
        lines = result.stdout.strip().split('\n')
        errors = []
        
        for line in lines:
            if ': E501' in line:
                parts = line.split(':')
                if len(parts) >= 3:
                    file_path = parts[0]
                    line_num = int(parts[1])
                    error_msg = parts[2].strip()
                    errors.append((file_path, line_num, error_msg))
        
        return errors
    except Exception as e:
        print(f"Error obteniendo errores E501: {e}")
        return []

def fix_line_length(file_path, line_num, error_msg):
    """Corregir una línea específica que excede 79 caracteres"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if line_num > len(lines):
            return False
        
        line = lines[line_num - 1]
        original_line = line.rstrip('\n')
        
        # Si la línea ya está corregida, saltar
        if len(original_line) <= 79:
            return False
        
        # Estrategias de corrección
        fixed_line = fix_long_line(original_line)
        
        if fixed_line != original_line:
            lines[line_num - 1] = fixed_line + '\n'
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            print(f"Corregido: {file_path}:{line_num}")
            return True
        
        return False
        
    except Exception as e:
        print(f"Error corrigiendo {file_path}:{line_num}: {e}")
        return False

def fix_long_line(line):
    """Aplicar estrategias para acortar líneas largas"""
    original_line = line
    
    # 1. Dividir strings largos
    if 'f"' in line and len(line) > 79:
        # Dividir f-strings largos
        line = split_f_string(line)
    
    # 2. Dividir llamadas de función largas
    if '(' in line and ')' in line and len(line) > 79:
        line = split_function_call(line)
    
    # 3. Dividir listas/diccionarios largos
    if ('[' in line or '{' in line) and len(line) > 79:
        line = split_collections(line)
    
    # 4. Dividir operadores lógicos
    if any(op in line for op in [' and ', ' or ', ' && ', ' || ']) and len(line) > 79:
        line = split_logical_operators(line)
    
    # 5. Dividir comentarios largos
    if line.strip().startswith('#') and len(line) > 79:
        line = split_comment(line)
    
    # 6. Dividir imports largos
    if line.strip().startswith(('import ', 'from ')) and len(line) > 79:
        line = split_import(line)
    
    # Si aún es muy larga, usar continuación de línea básica
    if len(line) > 79:
        line = basic_line_continuation(line)
    
    return line

def split_f_string(line):
    """Dividir f-strings largos"""
    # Buscar f-strings y dividirlos
    pattern = r'f"([^"]*)"'
    matches = list(re.finditer(pattern, line))
    
    for match in reversed(matches):
        f_string = match.group(1)
        if len(f_string) > 50:  # Solo dividir si es muy largo
            # Dividir el contenido del f-string
            parts = f_string.split(' ')
            if len(parts) > 3:
                mid = len(parts) // 2
                first_part = ' '.join(parts[:mid])
                second_part = ' '.join(parts[mid:])
                
                new_f_string = f'f"{first_part}" + f"{second_part}"'
                line = line[:match.start()] + new_f_string + line[match.end():]
    
    return line

def split_function_call(line):
    """Dividir llamadas de función largas"""
    # Buscar patrones de función con muchos argumentos
    if line.count(',') > 3 and '(' in line:
        # Encontrar la posición del primer paréntesis
        paren_pos = line.find('(')
        if paren_pos > 0:
            func_name = line[:paren_pos].strip()
            args_part = line[paren_pos:]
            
            # Dividir argumentos
            if len(args_part) > 60:
                # Dividir en múltiples líneas
                indent = ' ' * (len(line) - len(line.lstrip()))
                new_line = func_name + '(\n' + indent + '    ' + args_part[1:]
                return new_line
    
    return line

def split_collections(line):
    """Dividir listas y diccionarios largos"""
    # Buscar listas largas
    if '[' in line and ']' in line and line.count(',') > 2:
        bracket_pos = line.find('[')
        if bracket_pos > 0:
            prefix = line[:bracket_pos]
            content = line[bracket_pos:]
            
            if len(content) > 50:
                indent = ' ' * (len(line) - len(line.lstrip()))
                new_line = prefix + '[\n' + indent + '    ' + content[1:]
                return new_line
    
    return line

def split_logical_operators(line):
    """Dividir operadores lógicos"""
    for op in [' and ', ' or ']:
        if op in line:
            parts = line.split(op)
            if len(parts) == 2:
                indent = ' ' * (len(line) - len(line.lstrip()))
                new_line = parts[0] + op + '\n' + indent + parts[1]
                return new_line
    
    return line

def split_comment(line):
    """Dividir comentarios largos"""
    if line.strip().startswith('#'):
        comment_text = line.strip()[1:]
        if len(comment_text) > 70:
            words = comment_text.split()
            if len(words) > 5:
                mid = len(words) // 2
                first_part = ' '.join(words[:mid])
                second_part = ' '.join(words[mid:])
                
                indent = ' ' * (len(line) - len(line.lstrip()))
                new_line = indent + '# ' + first_part + '\n' + indent + '# ' + second_part
                return new_line
    
    return line

def split_import(line):
    """Dividir imports largos"""
    if 'from ' in line and ' import ' in line:
        parts = line.split(' import ')
        if len(parts) == 2:
            from_part = parts[0]
            import_part = parts[1]
            
            if len(import_part) > 50:
                # Dividir múltiples imports
                imports = [imp.strip() for imp in import_part.split(',')]
                if len(imports) > 1:
                    indent = ' ' * (len(line) - len(line.lstrip()))
                    new_line = from_part + ' import (\n'
                    for imp in imports:
                        new_line += indent + '    ' + imp + ',\n'
                    new_line += indent + ')'
                    return new_line
    
    return line

def basic_line_continuation(line):
    """Continuación básica de línea"""
    if len(line) > 79:
        # Buscar un buen punto de división
        for i in range(70, 79):
            if line[i] in [' ', ',', '(', '[', '{']:
                indent = ' ' * (len(line) - len(line.lstrip()))
                new_line = line[:i] + ' \\\n' + indent + line[i:].lstrip()
                return new_line
        
        # Si no hay buen punto, dividir en 70 caracteres
        indent = ' ' * (len(line) - len(line.lstrip()))
        new_line = line[:70] + ' \\\n' + indent + line[70:].lstrip()
        return new_line
    
    return line

def main():
    print("Iniciando corrección automática de errores E501...")
    
    errors = get_e501_errors()
    if not errors:
        print("No se encontraron errores E501.")
        return
    
    print(f"Encontrados {len(errors)} errores E501.")
    
    fixed_count = 0
    for file_path, line_num, error_msg in errors:
        if fix_line_length(file_path, line_num, error_msg):
            fixed_count += 1
    
    print(f"Corregidos {fixed_count} errores E501.")
    
    # Verificar errores restantes
    remaining_errors = get_e501_errors()
    print(f"Errores E501 restantes: {len(remaining_errors)}")

if __name__ == "__main__":
    main()
