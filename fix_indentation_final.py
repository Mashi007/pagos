#!/usr/bin/env python3
"""
Script para reescribir archivos con problemas de indentación
"""

import os
import re

def fix_file_indentation(file_path):
    """Corregir indentación de un archivo específico"""
    
    if not os.path.exists(file_path):
        print(f"ERROR: Archivo no encontrado: {file_path}")
        return False
    
    print(f"Corrigiendo {file_path}...")
    
    # Leer archivo con diferentes codificaciones
    content = None
    for encoding in ['utf-8', 'latin-1', 'cp1252']:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            print(f"  Leído con codificación: {encoding}")
            break
        except UnicodeDecodeError:
            continue
    
    if content is None:
        print(f"  ERROR: No se pudo leer el archivo con ninguna codificación")
        return False
    
    # Normalizar saltos de línea
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    
    # Corregir problemas específicos de indentación
    lines = content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        line_num = i + 1
        
        # Corregir problemas específicos por archivo
        if "intermittent_failure_analyzer.py" in file_path and line_num == 110:
            # Asegurar que la línea tenga exactamente 4 espacios
            stripped = line.strip()
            if stripped.startswith("def _analyze_endpoint_patterns"):
                fixed_line = "    " + stripped
                print(f"  CORREGIDO línea {line_num}: {stripped}")
                fixed_lines.append(fixed_line)
                continue
        
        elif "network_diagnostic.py" in file_path and line_num == 54:
            # Asegurar que la línea tenga exactamente 4 espacios
            stripped = line.strip()
            if stripped.startswith("def _test_connectivity"):
                fixed_line = "    " + stripped
                print(f"  CORREGIDO línea {line_num}: {stripped}")
                fixed_lines.append(fixed_line)
                continue
        
        elif "temporal_analysis.py" in file_path and line_num == 57:
            # Asegurar que la línea tenga exactamente 8 espacios
            stripped = line.strip()
            if "current_time = datetime.now()" in stripped:
                fixed_line = "        " + stripped
                print(f"  CORREGIDO línea {line_num}: {stripped}")
                fixed_lines.append(fixed_line)
                continue
        
        # Mantener línea original
        fixed_lines.append(line)
    
    # Escribir archivo corregido
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(fixed_lines))
        print(f"  OK: Archivo corregido y guardado")
        return True
    except Exception as e:
        print(f"  ERROR al escribir: {e}")
        return False

def main():
    """Función principal"""
    files_to_fix = [
        "backend/app/api/v1/endpoints/intermittent_failure_analyzer.py",
        "backend/app/api/v1/endpoints/network_diagnostic.py",
        "backend/app/api/v1/endpoints/temporal_analysis.py"
    ]
    
    total_fixed = 0
    
    for file_path in files_to_fix:
        if fix_file_indentation(file_path):
            total_fixed += 1
    
    print(f"\nRESUMEN: {total_fixed}/{len(files_to_fix)} archivos corregidos exitosamente")

if __name__ == "__main__":
    main()
