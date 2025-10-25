#!/usr/bin/env python3
"""
Script para corregir TODOS los errores de indentación en intermittent_failure_analyzer.py
"""

import re

def fix_all_indentation():
    """Corregir todos los errores de indentación de una vez"""
    
    file_path = "backend/app/api/v1/endpoints/intermittent_failure_analyzer.py"
    
    print(f"Corrigiendo TODOS los errores de indentacion en {file_path}")
    
    # Leer archivo
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Patrón para encontrar métodos mal indentados (4 espacios en lugar de 8)
    # Buscar líneas que empiecen con 4 espacios y contengan "def "
    pattern = r'^    def (\w+)\([^)]*\):'
    
    def replace_method(match):
        method_def = match.group(0)
        # Reemplazar 4 espacios iniciales con 8 espacios
        corrected = '        ' + method_def[4:]
        print(f"  Corregido metodo: {method_def.strip()}")
        return corrected
    
    # Aplicar la corrección
    corrected_content = re.sub(pattern, replace_method, content, flags=re.MULTILINE)
    
    # También corregir las líneas que están dentro de métodos mal indentados
    # Buscar líneas que empiecen con 4 espacios pero no sean "def " o "class "
    lines = corrected_content.split('\n')
    corrected_lines = []
    
    in_method = False
    method_indent = 0
    
    for line in lines:
        stripped = line.strip()
        
        # Si es un método (8 espacios + def), estamos dentro de un método
        if line.startswith('        def '):
            in_method = True
            method_indent = 8
            corrected_lines.append(line)
        # Si es una línea vacía o comentario, mantenerla
        elif not stripped or stripped.startswith('#'):
            corrected_lines.append(line)
        # Si estamos dentro de un método y la línea tiene contenido
        elif in_method and stripped:
            # Si la línea empieza con 4 espacios, corregirla a 12 espacios
            if line.startswith('    ') and not line.startswith('        '):
                corrected_line = '            ' + line[4:]
                corrected_lines.append(corrected_line)
            # Si la línea empieza con 8 espacios, corregirla a 12 espacios
            elif line.startswith('        ') and not line.startswith('            '):
                corrected_line = '            ' + line[8:]
                corrected_lines.append(corrected_line)
            else:
                corrected_lines.append(line)
        else:
            corrected_lines.append(line)
    
    # Unir las líneas
    final_content = '\n'.join(corrected_lines)
    
    # Escribir archivo corregido
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(final_content)
    
    print(f"  OK: Archivo {file_path} completamente corregido")

if __name__ == "__main__":
    print("Corrigiendo TODOS los errores de indentacion...")
    fix_all_indentation()
    print("Correccion completada")
