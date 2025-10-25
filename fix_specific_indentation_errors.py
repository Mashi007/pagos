#!/usr/bin/env python3
"""
Script para corregir errores de indentación específicos detectados por GitHub Actions
"""

import os
import re

def fix_indentation_errors():
    """Corregir errores de indentación específicos"""
    
    # Archivos con errores específicos
    files_to_fix = [
        {
            "file": "backend/app/api/v1/endpoints/critical_error_monitor.py",
            "line": 32,
            "description": "E999 IndentationError: unindent does not match any outer indentation level"
        },
        {
            "file": "backend/app/api/v1/endpoints/intermittent_failure_analyzer.py", 
            "line": 110,
            "description": "E999 IndentationError: unindent does not match any outer indentation level"
        },
        {
            "file": "backend/app/api/v1/endpoints/network_diagnostic.py",
            "line": 50, 
            "description": "E999 IndentationError: unindent does not match any outer indentation level"
        },
        {
            "file": "backend/app/api/v1/endpoints/temporal_analysis.py",
            "line": 50,
            "description": "E999 IndentationError: unindent does not match any outer indentation level"
        }
    ]
    
    for file_info in files_to_fix:
        file_path = file_info["file"]
        line_num = file_info["line"]
        
        print(f"Corrigiendo {file_path} linea {line_num}")
        
        if not os.path.exists(file_path):
            print(f"  ERROR: Archivo no encontrado: {file_path}")
            continue
            
        # Leer archivo
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if line_num > len(lines):
            print(f"  ERROR: Linea {line_num} no existe (archivo tiene {len(lines)} lineas)")
            continue
            
        # Mostrar contexto de la línea problemática
        start_context = max(0, line_num - 3)
        end_context = min(len(lines), line_num + 2)
        
        print(f"  Contexto alrededor de la linea {line_num}:")
        for i in range(start_context, end_context):
            marker = ">>> " if i == line_num - 1 else "    "
            print(f"  {marker}{i+1:3d}: {repr(lines[i])}")
        
        # Corregir indentación específica
        original_line = lines[line_num - 1]
        
        # Detectar el problema de indentación
        if original_line.strip():  # Si la línea no está vacía
            # Buscar la indentación correcta basada en el contexto
            # Generalmente es un problema de métodos de clase mal indentados
            
            # Buscar la línea anterior para determinar la indentación correcta
            for i in range(line_num - 2, -1, -1):
                if lines[i].strip() and not lines[i].strip().startswith('#'):
                    # Encontrar una línea con contenido
                    prev_line = lines[i]
                    if 'def ' in prev_line or 'class ' in prev_line:
                        # Es un método o clase, usar indentación de clase + 4 espacios
                        base_indent = len(prev_line) - len(prev_line.lstrip())
                        correct_indent = ' ' * (base_indent + 4)
                    else:
                        # Usar la misma indentación que la línea anterior
                        correct_indent = ' ' * (len(prev_line) - len(prev_line.lstrip()))
                    
                    # Corregir la línea problemática
                    content = original_line.strip()
                    lines[line_num - 1] = correct_indent + content + '\n'
                    
                    print(f"  CORREGIDO: '{original_line.rstrip()}' -> '{lines[line_num - 1].rstrip()}'")
                    break
        
        # Escribir archivo corregido
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        print(f"  OK: Archivo {file_path} corregido")
        print()

if __name__ == "__main__":
    print("Corrigiendo errores de indentacion especificos...")
    fix_indentation_errors()
    print("Correccion completada")
