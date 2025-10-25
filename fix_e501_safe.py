#!/usr/bin/env python3
"""
Script simple y seguro para corregir errores E501 restantes
Solo maneja casos específicos que sabemos que funcionan
"""

import os
import re
from pathlib import Path

def fix_simple_e501(line, max_length=79):
    """Corrige errores E501 simples y seguros"""
    original_line = line
    line = line.rstrip()
    
    # Si ya está dentro del límite, no hacer nada
    if len(line) <= max_length:
        return line
    
    # Solo manejar casos muy específicos y seguros
    
    # Caso 1: Comentarios largos
    if line.strip().startswith('#'):
        comment_content = line.strip()[1:].strip()
        if len(comment_content) > max_length - 4:
            # Dividir en palabras
            words = comment_content.split()
            if len(words) > 1:
                mid_point = len(words) // 2
                part1 = ' '.join(words[:mid_point])
                part2 = ' '.join(words[mid_point:])
                return f"# {part1}\n# {part2}"
    
    # Caso 2: Strings largos simples (no f-strings)
    if line.strip().startswith('"') and line.strip().endswith('"'):
        string_content = line.strip()[1:-1]
        if len(string_content) > max_length - 6:
            mid_point = len(string_content) // 2
            # Buscar un espacio cerca del punto medio
            for i in range(mid_point, len(string_content)):
                if string_content[i] == ' ':
                    part1 = string_content[:i]
                    part2 = string_content[i+1:]
                    return f'"{part1}"\n    "{part2}"'
    
    # Caso 3: Asignaciones simples
    if ' = ' in line and not any(char in line for char in ['(', '[', '{']):
        equal_pos = line.find(' = ')
        if equal_pos > 0 and equal_pos < max_length - 4:
            left_part = line[:equal_pos + 3]
            right_part = line[equal_pos + 3:].lstrip()
            return f"{left_part}\n    {right_part}"
    
    # Si no se puede manejar de forma segura, no hacer nada
    return original_line

def process_file_safely(file_path):
    """Procesa un archivo de forma segura"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        modified = False
        new_lines = []
        
        for line in lines:
            original_line = line
            new_line = fix_simple_e501(line)
            
            if new_line != original_line:
                modified = True
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
    
    # Solo procesar archivos específicos que sabemos que tienen problemas simples
    target_files = [
        "backend/app/core/__init__.py",
        "backend/app/db/base.py",
        "backend/app/models/modelo_vehiculo.py",
        "backend/app/schemas/modelo_vehiculo.py",
        "backend/app/schemas/reportes.py",
        "backend/app/schemas/user_simple.py",
        "backend/app/utils/__init__.py",
    ]
    
    print(f"Procesando {len(target_files)} archivos específicos...")
    
    modified_files = []
    
    for file_path in target_files:
        if os.path.exists(file_path):
            if process_file_safely(file_path):
                modified_files.append(file_path)
                print(f"Modificado: {file_path}")
        else:
            print(f"No encontrado: {file_path}")
    
    print(f"\nArchivos modificados: {len(modified_files)}")
    for file_path in modified_files:
        print(f"  - {file_path}")

if __name__ == "__main__":
    main()
