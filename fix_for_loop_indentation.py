#!/usr/bin/env python3
"""
Script específico para corregir líneas con indentación inconsistente dentro de bucles for
"""

import os

def fix_for_loop_indentation():
    """Corregir líneas con indentación inconsistente dentro de bucles for"""
    
    files_to_fix = [
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
        
        for i, line in enumerate(lines):
            line_num = i + 1
            
            # Detectar líneas que empiecen con 4 espacios pero deberían tener 8 (dentro de for)
            if line.startswith('    ') and not line.startswith('        '):
                stripped = line.strip()
                # Verificar si es parte de un bucle for
                if stripped.startswith('if ') or stripped.startswith('endpoint_stats[') or stripped.startswith('user_stats[') or stripped.startswith('hourly_stats[') or stripped.startswith('analysis[') or stripped.startswith('avg_successful') or stripped.startswith('avg_failed'):
                    # Corregir a 8 espacios
                    corrected_line = '        ' + stripped + '\n'
                    lines[i] = corrected_line
                    print(f"  CORREGIDO linea {line_num}: {stripped} (4->8 espacios)")
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
    print("Corrigiendo indentacion en bucles for...")
    fixed = fix_for_loop_indentation()
    print(f"Correccion completada. {fixed} problemas corregidos.")
