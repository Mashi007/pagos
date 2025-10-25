#!/usr/bin/env python3
"""
Script para corregir TODOS los errores de indentación en los 4 archivos
"""

import os
import re

def fix_file_indentation(file_path):
    """Corregir errores de indentación en un archivo específico"""
    
    print(f"Corrigiendo {file_path}")
    
    if not os.path.exists(file_path):
        print(f"  ERROR: Archivo no encontrado: {file_path}")
        return
    
    # Leer archivo
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    corrected_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Detectar métodos que están mal indentados
        if (line.strip().startswith('def ') and 
            line.startswith('    ') and 
            not line.startswith('        ') and
            i > 0 and 
            lines[i-1].strip() and 
            not lines[i-1].strip().startswith('#')):
            
            # Es un método mal indentado, corregirlo a 8 espacios
            content = line.strip()
            corrected_line = '        ' + content + '\n'
            corrected_lines.append(corrected_line)
            print(f"  Corregido metodo: {content}")
            
            # Corregir también las líneas siguientes hasta encontrar otro método o clase
            i += 1
            while i < len(lines):
                next_line = lines[i]
                
                # Si encontramos otro método o clase, parar
                if (next_line.strip().startswith('def ') or 
                    next_line.strip().startswith('class ') or
                    (next_line.strip() and not next_line.startswith(' ') and not next_line.startswith('\t'))):
                    break
                
                # Si la línea está vacía o es comentario, mantenerla
                if not next_line.strip() or next_line.strip().startswith('#'):
                    corrected_lines.append(next_line)
                else:
                    # Corregir indentación añadiendo 4 espacios más
                    if next_line.startswith('    '):
                        corrected_line = '        ' + next_line[4:]
                        corrected_lines.append(corrected_line)
                    else:
                        corrected_lines.append(next_line)
                
                i += 1
            
            # Retroceder uno para procesar la línea que causó el break
            i -= 1
        else:
            corrected_lines.append(line)
        
        i += 1
    
    # Escribir archivo corregido
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(corrected_lines)
    
    print(f"  OK: Archivo {file_path} corregido")

def fix_all_files():
    """Corregir todos los archivos con errores de indentación"""
    
    files_to_fix = [
        "backend/app/api/v1/endpoints/critical_error_monitor.py",
        "backend/app/api/v1/endpoints/intermittent_failure_analyzer.py", 
        "backend/app/api/v1/endpoints/network_diagnostic.py",
        "backend/app/api/v1/endpoints/temporal_analysis.py"
    ]
    
    for file_path in files_to_fix:
        fix_file_indentation(file_path)
        print()

if __name__ == "__main__":
    print("Corrigiendo TODOS los errores de indentacion...")
    fix_all_files()
    print("Correccion completada")
