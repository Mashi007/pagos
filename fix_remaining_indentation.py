#!/usr/bin/env python3
"""
Script para corregir errores de indentación específicos en archivos de endpoints
"""

import os
import re

def fix_indentation_errors():
    """Corregir errores de indentación específicos"""
    
    files_to_fix = [
        "backend/app/api/v1/endpoints/critical_error_monitor.py",
        "backend/app/api/v1/endpoints/intermittent_failure_analyzer.py", 
        "backend/app/api/v1/endpoints/network_diagnostic.py",
        "backend/app/api/v1/endpoints/temporal_analysis.py"
    ]
    
    for file_path in files_to_fix:
        if not os.path.exists(file_path):
            print(f"Archivo no encontrado: {file_path}")
            continue
            
        print(f"Corrigiendo: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Corregir métodos __init__ mal indentados
            # Buscar patrones donde __init__ está fuera de la clase
            lines = content.split('\n')
            fixed_lines = []
            in_class = False
            class_indent = 0
            
            for i, line in enumerate(lines):
                # Detectar inicio de clase
                if re.match(r'^class\s+\w+.*:', line):
                    in_class = True
                    class_indent = len(line) - len(line.lstrip())
                    fixed_lines.append(line)
                    continue
                
                # Detectar fin de clase (línea vacía o nueva clase)
                if in_class and (line.strip() == '' or re.match(r'^class\s+\w+.*:', line) or 
                                (line.strip() and not line.startswith(' ') and not line.startswith('\t'))):
                    in_class = False
                    class_indent = 0
                
                # Si estamos en una clase y encontramos __init__ mal indentado
                if in_class and '__init__' in line and 'def __init__' in line:
                    # Verificar si está mal indentado
                    current_indent = len(line) - len(line.lstrip())
                    if current_indent <= class_indent:
                        # Corregir indentación
                        correct_indent = ' ' * (class_indent + 4)
                        fixed_line = correct_indent + line.lstrip()
                        fixed_lines.append(fixed_line)
                        print(f"  Corregido __init__ en línea {i+1}")
                        continue
                
                fixed_lines.append(line)
            
            # Escribir archivo corregido
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(fixed_lines))
            
            print(f"  Archivo corregido: {file_path}")
            
        except Exception as e:
            print(f"  Error al corregir {file_path}: {e}")

if __name__ == "__main__":
    print("Iniciando corrección de errores de indentación...")
    fix_indentation_errors()
    print("Corrección completada!")
