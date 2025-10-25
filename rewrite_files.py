#!/usr/bin/env python3
"""
Script para reescribir completamente archivos con problemas de indentación
"""

import os
import shutil

def backup_and_rewrite_file(file_path):
    """Hacer backup y reescribir archivo completamente"""
    
    if not os.path.exists(file_path):
        print(f"ERROR: Archivo no encontrado: {file_path}")
        return False
    
    print(f"Reescribiendo {file_path}...")
    
    # Crear backup
    backup_path = file_path + ".backup"
    shutil.copy2(file_path, backup_path)
    print(f"  Backup creado: {backup_path}")
    
    # Leer contenido original
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        print(f"  ERROR al leer: {e}")
        return False
    
    # Normalizar contenido
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    
    # Reescribir con codificación limpia
    try:
        with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
        print(f"  OK: Archivo reescrito con codificación limpia")
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
        if backup_and_rewrite_file(file_path):
            total_fixed += 1
    
    print(f"\nRESUMEN: {total_fixed}/{len(files_to_fix)} archivos reescritos exitosamente")

if __name__ == "__main__":
    main()
