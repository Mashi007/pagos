#!/usr/bin/env python3
"""
Script para corregir errores de indentacion especificos
Busca y corrige metodos __init__ que estan fuera de sus clases
"""

import os
import re
import sys
from pathlib import Path

def fix_specific_indentation_errors(file_path):
    """Corregir errores especificos de indentacion"""
    print(f"Procesando: {file_path}")
    
    try:
        # Leer el archivo
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        original_lines = lines.copy()
        modified = False
        
        # Buscar y corregir patrones especificos
        for i, line in enumerate(lines):
            # Patron 1: def __init__(self): que deberia estar indentado
            if re.match(r'^def __init__\(self\):', line.strip()):
                # Verificar si la linea anterior es una clase
                if i > 0 and re.match(r'^class \w+', lines[i-1].strip()):
                    # Verificar si hay una docstring entre la clase y el metodo
                    j = i - 1
                    while j >= 0 and (lines[j].strip() == '' or lines[j].strip().startswith('"""') or lines[j].strip().startswith("'''")):
                        j -= 1
                    
                    if j >= 0 and re.match(r'^class \w+', lines[j].strip()):
                        # Corregir la indentacion
                        lines[i] = '    def __init__(self):\n'
                        modified = True
                        print(f"  Corregido __init__ en linea {i+1}")
            
            # Patron 2: @staticmethod seguido de def sin indentacion correcta
            elif re.match(r'^@staticmethod', line.strip()) and i+1 < len(lines):
                next_line = lines[i+1]
                if re.match(r'^def \w+', next_line.strip()):
                    lines[i] = '    @staticmethod\n'
                    lines[i+1] = '    def ' + next_line.split('def ', 1)[1]
                    modified = True
                    print(f"  Corregido @staticmethod en linea {i+1}")
        
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
    print("Iniciando correccion de errores de indentacion especificos...")
    
    # Directorio de endpoints
    endpoints_dir = Path("backend/app/api/v1/endpoints")
    
    if not endpoints_dir.exists():
        print(f"ERROR: Directorio no encontrado: {endpoints_dir}")
        return
    
    # Archivos a procesar
    files_to_fix = [
        "dashboard_diagnostico.py",
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
            if fix_specific_indentation_errors(file_path):
                fixed_count += 1
        else:
            print(f"ADVERTENCIA: Archivo no encontrado: {file_path}")
    
    print(f"\nRESUMEN:")
    print(f"   Archivos procesados: {len(files_to_fix)}")
    print(f"   Archivos corregidos: {fixed_count}")
    print(f"   Archivos sin cambios: {len(files_to_fix) - fixed_count}")

if __name__ == "__main__":
    main()
