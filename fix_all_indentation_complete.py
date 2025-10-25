#!/usr/bin/env python3
"""
Script completo para corregir todos los problemas de indentación en los archivos problemáticos
"""

import os
import re

def fix_all_indentation_issues():
    """Corregir todos los problemas de indentación identificados"""
    
    files_to_fix = [
        "backend/app/api/v1/endpoints/critical_error_monitor.py",
        "backend/app/api/v1/endpoints/intermittent_failure_analyzer.py", 
        "backend/app/api/v1/endpoints/network_diagnostic.py",
        "backend/app/api/v1/endpoints/temporal_analysis.py"
    ]
    
    total_fixed = 0
    
    for file_path in files_to_fix:
        print(f"Corrigiendo {file_path}...")
        
        if not os.path.exists(file_path):
            print(f"  ERROR: Archivo no encontrado: {file_path}")
            continue
        
        # Leer archivo
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        fixed_count = 0
        
        # Procesar línea por línea
        for i, line in enumerate(lines):
            line_num = i + 1
            original_line = line
            
            # Detectar y corregir diferentes patrones de indentación incorrecta
            
            # 1. Métodos que tienen 8 espacios pero deberían tener 4 (fuera de clase)
            if line.startswith('        ') and 'def ' in line and not line.startswith('            '):
                # Verificar si estamos dentro de una clase
                in_class = False
                for j in range(i-1, -1, -1):
                    if lines[j].strip().startswith('class '):
                        in_class = True
                        break
                    elif lines[j].strip().startswith('def ') and not lines[j].startswith('        '):
                        break
                
                if not in_class:
                    stripped = line.strip()
                    corrected_line = '    ' + stripped + '\n'
                    lines[i] = corrected_line
                    print(f"  CORREGIDO linea {line_num}: {stripped} (8->4 espacios)")
                    fixed_count += 1
            
            # 2. Métodos que tienen 4 espacios pero deberían tener 8 (dentro de clase)
            elif line.startswith('    ') and 'def ' in line and not line.startswith('        '):
                # Verificar si estamos dentro de una clase
                in_class = False
                for j in range(i-1, -1, -1):
                    if lines[j].strip().startswith('class '):
                        in_class = True
                        break
                    elif lines[j].strip().startswith('def ') and not lines[j].startswith('        '):
                        break
                
                if in_class:
                    stripped = line.strip()
                    corrected_line = '        ' + stripped + '\n'
                    lines[i] = corrected_line
                    print(f"  CORREGIDO linea {line_num}: {stripped} (4->8 espacios)")
                    fixed_count += 1
            
            # 3. Líneas que tienen indentación inconsistente después de definiciones de función
            elif 'def ' in line and line.strip().endswith(':'):
                # Buscar la siguiente línea no vacía
                next_line_idx = i + 1
                while next_line_idx < len(lines) and not lines[next_line_idx].strip():
                    next_line_idx += 1
                
                if next_line_idx < len(lines):
                    next_line = lines[next_line_idx]
                    if next_line.strip() and not next_line.startswith('    '):
                        # La siguiente línea debería estar indentada
                        stripped = next_line.strip()
                        corrected_line = '    ' + stripped + '\n'
                        lines[next_line_idx] = corrected_line
                        print(f"  CORREGIDO linea {next_line_idx + 1}: {stripped} (agregada indentacion)")
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
    print("Corrigiendo todos los problemas de indentacion...")
    fixed = fix_all_indentation_issues()
    print(f"Correccion completada. {fixed} problemas corregidos.")
