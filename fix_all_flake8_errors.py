#!/usr/bin/env python3
"""
Script para corregir TODOS los errores de flake8 sistemáticamente
Corrige en orden de prioridad para evitar efectos yo-yo
"""

import os
import re
import subprocess
from pathlib import Path

def run_flake8():
    """Ejecutar flake8 y obtener errores"""
    try:
        result = subprocess.run([
            'py', '-m', 'flake8', 'app/', '--count', '--exit-zero', 
            '--max-complexity=10', '--max-line-length=127', '--statistics'
        ], capture_output=True, text=True, cwd='backend')
        return result.stdout
    except Exception as e:
        print(f"Error ejecutando flake8: {e}")
        return ""

def fix_whitespace_in_blank_lines(file_path):
    """Corregir W293: blank line contains whitespace"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        fixed = False
        for i, line in enumerate(lines):
            if line.strip() == '' and line != '\n':
                lines[i] = '\n'
                fixed = True
        
        if fixed:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            return True
    except Exception as e:
        print(f"Error corrigiendo {file_path}: {e}")
    return False

def fix_trailing_whitespace(file_path):
    """Corregir W291: trailing whitespace"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        fixed = False
        for i, line in enumerate(lines):
            if line.rstrip() != line.rstrip('\n'):
                lines[i] = line.rstrip() + '\n'
                fixed = True
        
        if fixed:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            return True
    except Exception as e:
        print(f"Error corrigiendo {file_path}: {e}")
    return False

def fix_missing_newline_at_end(file_path):
    """Corregir W292: no newline at end of file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if content and not content.endswith('\n'):
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content + '\n')
            return True
    except Exception as e:
        print(f"Error corrigiendo {file_path}: {e}")
    return False

def fix_function_spacing(file_path):
    """Corregir E302/E305: expected 2 blank lines"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        fixed = False
        i = 0
        while i < len(lines) - 1:
            line = lines[i].strip()
            
            # Detectar definiciones de función/clase
            if (line.startswith('def ') or line.startswith('class ') or 
                line.startswith('async def ')):
                
                # Buscar hacia atrás para contar líneas vacías
                blank_count = 0
                j = i - 1
                while j >= 0 and lines[j].strip() == '':
                    blank_count += 1
                    j -= 1
                
                # Si es la primera función/clase del archivo, no necesita líneas vacías
                if j < 0:
                    i += 1
                    continue
                
                # Si hay código antes, necesita 2 líneas vacías
                if blank_count < 2:
                    # Insertar líneas vacías necesarias
                    needed_lines = 2 - blank_count
                    for _ in range(needed_lines):
                        lines.insert(i, '\n')
                        i += 1
                    fixed = True
            
            i += 1
        
        if fixed:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            return True
    except Exception as e:
        print(f"Error corrigiendo {file_path}: {e}")
    return False

def fix_long_lines(file_path):
    """Corregir E501: line too long"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        fixed = False
        for i, line in enumerate(lines):
            if len(line.rstrip()) > 127:
                # Estrategia simple: dividir en comentarios largos
                if line.strip().startswith('#'):
                    # Dividir comentarios largos
                    if len(line.strip()) > 130:
                        comment = line.strip()[1:]  # Quitar #
                        words = comment.split()
                        new_lines = []
                        current_line = '# '
                        
                        for word in words:
                            if len(current_line + word) > 125:
                                new_lines.append(current_line.rstrip() + '\n')
                                current_line = '# ' + word + ' '
                            else:
                                current_line += word + ' '
                        
                        if current_line.strip() != '#':
                            new_lines.append(current_line.rstrip() + '\n')
                        
                        lines[i] = ''.join(new_lines)
                        fixed = True
        
        if fixed:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            return True
    except Exception as e:
        print(f"Error corrigiendo {file_path}: {e}")
    return False

def fix_unused_imports(file_path):
    """Corregir F401: imported but unused"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        fixed = False
        imports_to_remove = []
        
        # Buscar imports no usados (estrategia simple)
        for i, line in enumerate(lines):
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                # Extraer nombre del import
                if ' as ' in line:
                    import_name = line.split(' as ')[1].strip().split()[0]
                elif 'import ' in line:
                    import_name = line.split('import ')[1].strip().split(',')[0].strip()
                else:
                    continue
                
                # Verificar si se usa en el resto del archivo
                content_after = ''.join(lines[i+1:])
                if import_name not in content_after:
                    imports_to_remove.append(i)
        
        # Remover imports no usados
        for i in reversed(imports_to_remove):
            del lines[i]
            fixed = True
        
        if fixed:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            return True
    except Exception as e:
        print(f"Error corrigiendo {file_path}: {e}")
    return False

def fix_all_errors():
    """Corregir todos los errores sistemáticamente"""
    print("INICIANDO CORRECCION SISTEMATICA DE TODOS LOS ERRORES")
    print("=" * 60)
    
    # Obtener lista de archivos Python
    backend_path = Path("backend")
    python_files = list(backend_path.rglob("*.py"))
    
    total_files = len(python_files)
    print(f"Archivos Python encontrados: {total_files}")
    
    # Paso 1: Corregir espacios en líneas vacías (W293)
    print("\nPaso 1: Corrigiendo espacios en lineas vacias (W293)...")
    fixed_w293 = 0
    for file_path in python_files:
        if fix_whitespace_in_blank_lines(file_path):
            fixed_w293 += 1
    print(f"Archivos corregidos: {fixed_w293}")
    
    # Paso 2: Corregir espacios al final (W291)
    print("\nPaso 2: Corrigiendo espacios al final (W291)...")
    fixed_w291 = 0
    for file_path in python_files:
        if fix_trailing_whitespace(file_path):
            fixed_w291 += 1
    print(f"Archivos corregidos: {fixed_w291}")
    
    # Paso 3: Corregir falta de salto de línea (W292)
    print("\nPaso 3: Corrigiendo falta de salto de linea (W292)...")
    fixed_w292 = 0
    for file_path in python_files:
        if fix_missing_newline_at_end(file_path):
            fixed_w292 += 1
    print(f"Archivos corregidos: {fixed_w292}")
    
    # Paso 4: Corregir espaciado entre funciones (E302/E305)
    print("\nPaso 4: Corrigiendo espaciado entre funciones (E302/E305)...")
    fixed_e302 = 0
    for file_path in python_files:
        if fix_function_spacing(file_path):
            fixed_e302 += 1
    print(f"Archivos corregidos: {fixed_e302}")
    
    # Paso 5: Corregir líneas largas (E501)
    print("\nPaso 5: Corrigiendo lineas largas (E501)...")
    fixed_e501 = 0
    for file_path in python_files:
        if fix_long_lines(file_path):
            fixed_e501 += 1
    print(f"Archivos corregidos: {fixed_e501}")
    
    # Paso 6: Corregir imports no usados (F401)
    print("\nPaso 6: Corrigiendo imports no usados (F401)...")
    fixed_f401 = 0
    for file_path in python_files:
        if fix_unused_imports(file_path):
            fixed_f401 += 1
    print(f"Archivos corregidos: {fixed_f401}")
    
    print("\n" + "=" * 60)
    print("RESUMEN DE CORRECCIONES:")
    print(f"   W293 (espacios en lineas vacias): {fixed_w293} archivos")
    print(f"   W291 (espacios al final): {fixed_w291} archivos")
    print(f"   W292 (falta salto de linea): {fixed_w292} archivos")
    print(f"   E302/E305 (espaciado funciones): {fixed_e302} archivos")
    print(f"   E501 (lineas largas): {fixed_e501} archivos")
    print(f"   F401 (imports no usados): {fixed_f401} archivos")
    
    # Verificar resultado
    print("\nVerificando resultado...")
    flake8_output = run_flake8()
    error_count = len([line for line in flake8_output.split('\n') if ':' in line])
    
    print(f"Errores restantes: {error_count}")
    
    if error_count == 0:
        print("TODOS LOS ERRORES CORREGIDOS!")
    else:
        print("Aun quedan errores por corregir")
        print("Primeras lineas de errores restantes:")
        for line in flake8_output.split('\n')[:10]:
            if ':' in line:
                print(f"   {line}")

if __name__ == "__main__":
    fix_all_errors()