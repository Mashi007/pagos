#!/usr/bin/env python3
"""
Script para verificar caracteres invisibles y problemas de indentación
"""

import os

def check_indentation_issues():
    """Verificar problemas de indentación en archivos específicos"""
    
    files_to_check = [
        "backend/app/api/v1/endpoints/intermittent_failure_analyzer.py",
        "backend/app/api/v1/endpoints/network_diagnostic.py",
        "backend/app/api/v1/endpoints/temporal_analysis.py"
    ]
    
    for file_path in files_to_check:
        print(f"Verificando {file_path}...")
        
        if not os.path.exists(file_path):
            print(f"  ERROR: Archivo no encontrado: {file_path}")
            continue
        
        # Leer archivo
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Verificar líneas problemáticas específicas
        problem_lines = [110, 54, 57]  # Líneas reportadas por flake8
        
        for line_num in problem_lines:
            if line_num <= len(lines):
                line = lines[line_num - 1]  # Convertir a índice 0-based
                print(f"  Linea {line_num}: {repr(line)}")
                
                # Verificar caracteres invisibles
                for i, char in enumerate(line):
                    if ord(char) > 127 or char in ['\t', '\r', '\n']:
                        print(f"    Caracter especial en posicion {i}: {repr(char)} (ord: {ord(char)})")
        
        print()

if __name__ == "__main__":
    print("Verificando problemas de indentacion...")
    check_indentation_issues()
    print("Verificacion completada.")
