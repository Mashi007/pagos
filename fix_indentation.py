#!/usr/bin/env python3
"""
Script para corregir errores de indentacion en archivos Python
Corrige especificamente metodos __init__ que estan fuera de sus clases
"""

import os
import re
import sys
from pathlib import Path

def fix_indentation_errors(file_path):
    """Corregir errores de indentacion en un archivo Python"""
    print(f"Procesando: {file_path}")
    
    try:
        # Leer el archivo
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Patrones de correccion
        patterns = [
            # Corregir metodos __init__ fuera de clases
            (r'(\nclass \w+.*?\n.*?"""[^"]*"""\s*\n)\ndef __init__\(self\):', 
             r'\1    def __init__(self):'),
            
            # Corregir otros metodos fuera de clases
            (r'(\nclass \w+.*?\n.*?"""[^"]*"""\s*\n)\ndef (\w+)\(self\):', 
             r'\1    def \2(self):'),
            
            # Corregir metodos estaticos fuera de clases
            (r'(\nclass \w+.*?\n.*?"""[^"]*"""\s*\n)\n@staticmethod\ndef (\w+)\(', 
             r'\1    @staticmethod\n    def \2('),
            
            # Corregir funciones internas mal indentadas
            (r'(\n    def \w+.*?\n.*?"""[^"]*"""\s*\n)\ndef (\w+)\(', 
             r'\1        def \2('),
        ]
        
        # Aplicar correcciones
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
        
        # Verificar si hubo cambios
        if content != original_content:
            # Escribir el archivo corregido
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
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
    print("Iniciando correccion de errores de indentacion...")
    
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
            if fix_indentation_errors(file_path):
                fixed_count += 1
        else:
            print(f"ADVERTENCIA: Archivo no encontrado: {file_path}")
    
    print(f"\nRESUMEN:")
    print(f"   Archivos procesados: {len(files_to_fix)}")
    print(f"   Archivos corregidos: {fixed_count}")
    print(f"   Archivos sin cambios: {len(files_to_fix) - fixed_count}")

if __name__ == "__main__":
    main()