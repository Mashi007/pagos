#!/usr/bin/env python3
"""
Script avanzado para corregir los errores E501 restantes
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

def fix_line_length_advanced(file_path, line_num, error_msg):
    """Corregir una línea específica usando estrategias avanzadas"""
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
        
        # Estrategias avanzadas de corrección
        fixed_line = apply_advanced_fixes(original_line, file_path)
        
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

def apply_advanced_fixes(line, file_path):
    """Aplicar estrategias avanzadas para acortar líneas"""
    
    # 1. Dividir strings muy largos en múltiples líneas
    if 'f"' in line and len(line) > 100:
        line = split_long_f_string(line)
    
    # 2. Dividir llamadas de función con muchos argumentos
    if line.count(',') > 4 and '(' in line and ')' in line:
        line = split_function_with_many_args(line)
    
    # 3. Dividir diccionarios largos
    if '{' in line and '}' in line and line.count(',') > 3:
        line = split_long_dict(line)
    
    # 4. Dividir listas largas
    if '[' in line and ']' in line and line.count(',') > 3:
        line = split_long_list(line)
    
    # 5. Dividir operaciones de concatenación
    if ' + ' in line and len(line) > 90:
        line = split_concatenation(line)
    
    # 6. Dividir condiciones complejas
    if any(op in line for op in [' and ', ' or ', ' && ', ' || ']) and len(line) > 90:
        line = split_complex_condition(line)
    
    # 7. Dividir imports largos
    if line.strip().startswith(('import ', 'from ')) and len(line) > 90:
        line = split_long_import(line)
    
    # 8. Dividir comentarios largos
    if line.strip().startswith('#') and len(line) > 90:
        line = split_long_comment(line)
    
    # 9. Dividir URLs o paths largos
    if ('http' in line or 'www.' in line or '/api/' in line) and len(line) > 90:
        line = split_long_url(line)
    
    # 10. Usar continuación de línea básica como último recurso
    if len(line) > 79:
        line = smart_line_continuation(line)
    
    return line

def split_long_f_string(line):
    """Dividir f-strings muy largos"""
    # Buscar f-strings largos
    pattern = r'f"([^"]{50,})"'
    matches = list(re.finditer(pattern, line))
    
    for match in reversed(matches):
        f_content = match.group(1)
        if len(f_content) > 50:
            # Dividir el contenido en partes más pequeñas
            words = f_content.split()
            if len(words) > 4:
                mid = len(words) // 2
                first_part = ' '.join(words[:mid])
                second_part = ' '.join(words[mid:])
                
                new_f_string = f'f"{first_part}" + f"{second_part}"'
                line = line[:match.start()] + new_f_string + line[match.end():]
    
    return line

def split_function_with_many_args(line):
    """Dividir funciones con muchos argumentos"""
    if '(' in line and ')' in line:
        paren_start = line.find('(')
        paren_end = line.rfind(')')
        
        if paren_start > 0 and paren_end > paren_start:
            func_name = line[:paren_start].strip()
            args_content = line[paren_start+1:paren_end]
            
            if len(args_content) > 60:
                # Dividir argumentos
                args = [arg.strip() for arg in args_content.split(',')]
                if len(args) > 3:
                    indent = ' ' * (len(line) - len(line.lstrip()))
                    
                    # Crear múltiples líneas
                    new_line = func_name + '(\n'
                    for i, arg in enumerate(args):
                        if i == len(args) - 1:
                            new_line += indent + '    ' + arg + '\n'
                        else:
                            new_line += indent + '    ' + arg + ',\n'
                    new_line += indent + ')'
                    return new_line
    
    return line

def split_long_dict(line):
    """Dividir diccionarios largos"""
    if '{' in line and '}' in line:
        brace_start = line.find('{')
        brace_end = line.rfind('}')
        
        if brace_start > 0 and brace_end > brace_start:
            prefix = line[:brace_start]
            dict_content = line[brace_start+1:brace_end]
            
            if len(dict_content) > 50:
                # Dividir elementos del diccionario
                items = [item.strip() for item in dict_content.split(',')]
                if len(items) > 2:
                    indent = ' ' * (len(line) - len(line.lstrip()))
                    
                    new_line = prefix + '{\n'
                    for i, item in enumerate(items):
                        if i == len(items) - 1:
                            new_line += indent + '    ' + item + '\n'
                        else:
                            new_line += indent + '    ' + item + ',\n'
                    new_line += indent + '}'
                    return new_line
    
    return line

def split_long_list(line):
    """Dividir listas largas"""
    if '[' in line and ']' in line:
        bracket_start = line.find('[')
        bracket_end = line.rfind(']')
        
        if bracket_start > 0 and bracket_end > bracket_start:
            prefix = line[:bracket_start]
            list_content = line[bracket_start+1:bracket_end]
            
            if len(list_content) > 50:
                # Dividir elementos de la lista
                items = [item.strip() for item in list_content.split(',')]
                if len(items) > 2:
                    indent = ' ' * (len(line) - len(line.lstrip()))
                    
                    new_line = prefix + '[\n'
                    for i, item in enumerate(items):
                        if i == len(items) - 1:
                            new_line += indent + '    ' + item + '\n'
                        else:
                            new_line += indent + '    ' + item + ',\n'
                    new_line += indent + ']'
                    return new_line
    
    return line

def split_concatenation(line):
    """Dividir operaciones de concatenación"""
    if ' + ' in line:
        parts = line.split(' + ')
        if len(parts) == 2:
            indent = ' ' * (len(line) - len(line.lstrip()))
            new_line = parts[0] + ' + \\\n' + indent + parts[1]
            return new_line
    
    return line

def split_complex_condition(line):
    """Dividir condiciones complejas"""
    for op in [' and ', ' or ']:
        if op in line:
            parts = line.split(op)
            if len(parts) == 2:
                indent = ' ' * (len(line) - len(line.lstrip()))
                new_line = parts[0] + op + '\\\n' + indent + parts[1]
                return new_line
    
    return line

def split_long_import(line):
    """Dividir imports largos"""
    if 'from ' in line and ' import ' in line:
        parts = line.split(' import ')
        if len(parts) == 2:
            from_part = parts[0]
            import_part = parts[1]
            
            if len(import_part) > 50:
                imports = [imp.strip() for imp in import_part.split(',')]
                if len(imports) > 1:
                    indent = ' ' * (len(line) - len(line.lstrip()))
                    new_line = from_part + ' import (\n'
                    for imp in imports:
                        new_line += indent + '    ' + imp + ',\n'
                    new_line += indent + ')'
                    return new_line
    
    return line

def split_long_comment(line):
    """Dividir comentarios largos"""
    if line.strip().startswith('#'):
        comment_text = line.strip()[1:]
        if len(comment_text) > 70:
            words = comment_text.split()
            if len(words) > 8:
                mid = len(words) // 2
                first_part = ' '.join(words[:mid])
                second_part = ' '.join(words[mid:])
                
                indent = ' ' * (len(line) - len(line.lstrip()))
                new_line = indent + '# ' + first_part + '\n' + indent + '# ' + second_part
                return new_line
    
    return line

def split_long_url(line):
    """Dividir URLs o paths largos"""
    # Buscar URLs o paths largos
    url_patterns = [
        r'https?://[^\s]+',
        r'/api/[^\s]+',
        r'www\.[^\s]+'
    ]
    
    for pattern in url_patterns:
        matches = list(re.finditer(pattern, line))
        for match in reversed(matches):
            url = match.group(0)
            if len(url) > 60:
                # Dividir URL en partes más pequeñas
                parts = url.split('/')
                if len(parts) > 3:
                    mid = len(parts) // 2
                    first_part = '/'.join(parts[:mid])
                    second_part = '/'.join(parts[mid:])
                    
                    new_url = first_part + '/\\\n    ' + second_part
                    line = line[:match.start()] + new_url + line[match.end():]
    
    return line

def smart_line_continuation(line):
    """Continuación inteligente de línea"""
    if len(line) > 79:
        # Buscar el mejor punto de división
        best_pos = 70
        for i in range(70, 79):
            if line[i] in [' ', ',', '(', '[', '{', '=']:
                best_pos = i
                break
        
        if best_pos < 79:
            indent = ' ' * (len(line) - len(line.lstrip()))
            new_line = line[:best_pos] + ' \\\n' + indent + line[best_pos:].lstrip()
            return new_line
        
        # Si no hay buen punto, dividir en 70 caracteres
        indent = ' ' * (len(line) - len(line.lstrip()))
        new_line = line[:70] + ' \\\n' + indent + line[70:].lstrip()
        return new_line
    
    return line

def main():
    print("Iniciando corrección avanzada de errores E501...")
    
    errors = get_e501_errors()
    if not errors:
        print("No se encontraron errores E501.")
        return
    
    print(f"Encontrados {len(errors)} errores E501.")
    
    fixed_count = 0
    for file_path, line_num, error_msg in errors:
        if fix_line_length_advanced(file_path, line_num, error_msg):
            fixed_count += 1
    
    print(f"Corregidos {fixed_count} errores E501.")
    
    # Verificar errores restantes
    remaining_errors = get_e501_errors()
    print(f"Errores E501 restantes: {len(remaining_errors)}")

if __name__ == "__main__":
    main()
