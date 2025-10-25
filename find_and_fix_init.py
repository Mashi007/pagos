#!/usr/bin/env python3
"""
Script para buscar y corregir metodos __init__ mal indentados
Busca patrones especificos y los corrige
"""

import os
import re
import sys
from pathlib import Path

def find_and_fix_init_methods(file_path):
    """Buscar y corregir metodos __init__ mal indentados"""
    print(f"Analizando: {file_path}")
    
    try:
        # Leer el archivo
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        modified = False
        
        # Buscar patrones problemáticos
        for i, line in enumerate(lines):
            # Buscar def __init__(self): que no esté indentado correctamente
            if re.match(r'^def __init__\(self\):', line.strip()):
                print(f"  Encontrado __init__ en linea {i+1}: '{line.strip()}'")
                
                # Verificar si debería estar indentado
                # Buscar hacia atrás para encontrar la clase
                j = i - 1
                found_class = False
                
                while j >= 0:
                    current_line = lines[j].strip()
                    
                    # Si encontramos una clase
                    if re.match(r'^class \w+', current_line):
                        found_class = True
                        print(f"    Clase encontrada en linea {j+1}: '{current_line}'")
                        break
                    
                    # Si encontramos otra definición de función/clase, no es parte de esta clase
                    if re.match(r'^(def |class )', current_line):
                        break
                    
                    j -= 1
                
                if found_class:
                    # Verificar si hay una docstring entre la clase y el método
                    has_docstring = False
                    for k in range(j+1, i):
                        if lines[k].strip().startswith('"""') or lines[k].strip().startswith("'''"):
                            has_docstring = True
                            break
                    
                    # Si debería estar indentado, corregirlo
                    if not line.startswith('    '):
                        lines[i] = '    def __init__(self):\n'
                        modified = True
                        print(f"    CORREGIDO: Indentacion en linea {i+1}")
        
        # Escribir el archivo si hubo cambios
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            print(f"CORREGIDO: {file_path}")
            return True
        else:
            print(f"SIN CAMBIOS: {file_path}")
            return False
            
    except Exception as e:
        print(f"ERROR procesando {file_path}: {e}")
        return False

def main():
    """Funcion principal"""
    print("Buscando metodos __init__ mal indentados...")
    
    # Directorio de endpoints
    endpoints_dir = Path("backend/app/api/v1/endpoints")
    
    if not endpoints_dir.exists():
        print(f"ERROR: Directorio no encontrado: {endpoints_dir}")
        return
    
    # Archivos a procesar
    files_to_fix = [
        "forensic_analysis.py", 
        "intelligent_alerts.py",
        "intermittent_failure_analyzer.py",
        "network_diagnostic.py",
        "predictive_token_analyzer.py",
        "real_time_monitor.py",
        "realtime_specific_monitor.py",
        "temporal_analysis.py"
    ]
    
    fixed_count = 0
    
    for filename in files_to_fix:
        file_path = endpoints_dir / filename
        if file_path.exists():
            if find_and_fix_init_methods(file_path):
                fixed_count += 1
        else:
            print(f"ADVERTENCIA: Archivo no encontrado: {file_path}")
    
    print(f"\nRESUMEN:")
    print(f"   Archivos procesados: {len(files_to_fix)}")
    print(f"   Archivos corregidos: {fixed_count}")
    print(f"   Archivos sin cambios: {len(files_to_fix) - fixed_count}")

if __name__ == "__main__":
    main()
