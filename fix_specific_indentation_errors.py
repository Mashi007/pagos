#!/usr/bin/env python3
"""
Script para corregir específicamente los errores de indentación reportados por flake8
"""

import os
import re

def fix_specific_indentation_errors():
    """Corregir errores específicos de indentación reportados por flake8"""
    
    files_to_fix = [
        ("backend/app/api/v1/endpoints/intermittent_failure_analyzer.py", 110),
        ("backend/app/api/v1/endpoints/network_diagnostic.py", 54),
        ("backend/app/api/v1/endpoints/temporal_analysis.py", 57)
    ]
    
    total_fixed = 0
    
    for file_path, problem_line in files_to_fix:
        print(f"Corrigiendo {file_path} linea {problem_line}...")
        
        if not os.path.exists(file_path):
            print(f"  ERROR: Archivo no encontrado: {file_path}")
            continue
        
        # Leer archivo
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        fixed_count = 0
        
        # Corregir línea específica
        if problem_line <= len(lines):
            line_idx = problem_line - 1  # Convertir a índice 0-based
            original_line = lines[line_idx]
            
            # Detectar y corregir problemas de indentación
            if file_path.endswith("intermittent_failure_analyzer.py") and problem_line == 110:
                # Verificar si la línea tiene indentación incorrecta
                if original_line.startswith('    ') and not original_line.startswith('        '):
                    # Corregir a 4 espacios
                    stripped = original_line.strip()
                    corrected_line = '    ' + stripped + '\n'
                    lines[line_idx] = corrected_line
                    print(f"  CORREGIDO linea {problem_line}: {stripped}")
                    fixed_count += 1
            
            elif file_path.endswith("network_diagnostic.py") and problem_line == 54:
                # Verificar si la línea tiene indentación incorrecta
                if original_line.startswith('    ') and not original_line.startswith('        '):
                    # Corregir a 4 espacios
                    stripped = original_line.strip()
                    corrected_line = '    ' + stripped + '\n'
                    lines[line_idx] = corrected_line
                    print(f"  CORREGIDO linea {problem_line}: {stripped}")
                    fixed_count += 1
            
            elif file_path.endswith("temporal_analysis.py") and problem_line == 57:
                # Verificar si la línea tiene indentación incorrecta
                if original_line.startswith('        ') and not original_line.startswith('            '):
                    # Corregir a 8 espacios
                    stripped = original_line.strip()
                    corrected_line = '        ' + stripped + '\n'
                    lines[line_idx] = corrected_line
                    print(f"  CORREGIDO linea {problem_line}: {stripped}")
                    fixed_count += 1
        
        # Escribir archivo corregido
        if fixed_count > 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            print(f"  OK: {fixed_count} problemas corregidos en {file_path}")
            total_fixed += fixed_count
        else:
            print(f"  OK: No se encontraron problemas en {file_path}")
    
    print(f"\nRESUMEN: Total de problemas corregidos: {total_fixed}")
    return total_fixed

if __name__ == "__main__":
    print("Corrigiendo errores especificos de indentacion...")
    fixed = fix_specific_indentation_errors()
    print(f"Correccion completada. {fixed} problemas corregidos.")