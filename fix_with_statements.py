#!/usr/bin/env python3
"""
Script para corregir errores de 'with' statements mal indentados
"""

def fix_with_statements(file_path):
    """Corregir errores de 'with' statements mal indentados"""
    
    print(f"Corrigiendo 'with' statements en {file_path}")
    
    # Leer archivo
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    corrected_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Detectar líneas que empiecen con 'with' y la siguiente línea no esté indentada
        if (line.strip().startswith('with ') and 
            i + 1 < len(lines) and 
            lines[i + 1].strip() and 
            not lines[i + 1].startswith('    ') and 
            not lines[i + 1].startswith('\t')):
            
            # Es un 'with' statement mal indentado
            corrected_lines.append(line)
            print(f"  Corregido 'with' statement en linea {i + 1}")
            
            # Corregir la siguiente línea añadiendo indentación
            i += 1
            next_line = lines[i]
            if next_line.strip():
                corrected_line = '                ' + next_line.strip() + '\n'
                corrected_lines.append(corrected_line)
                print(f"  Corregida indentacion en linea {i + 1}")
        else:
            corrected_lines.append(line)
        
        i += 1
    
    # Escribir archivo corregido
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(corrected_lines)
    
    print(f"  OK: Archivo {file_path} corregido")

if __name__ == "__main__":
    print("Corrigiendo 'with' statements...")
    fix_with_statements("backend/app/api/v1/endpoints/intermittent_failure_analyzer.py")
    print("Correccion completada")
