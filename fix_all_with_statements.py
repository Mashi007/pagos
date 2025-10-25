#!/usr/bin/env python3
"""
Script para corregir TODOS los errores de 'with' statements mal indentados
"""

def fix_all_with_statements(file_path):
    """Corregir TODOS los errores de 'with' statements mal indentados"""
    
    print(f"Corrigiendo TODOS los 'with' statements en {file_path}")
    
    # Leer archivo
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Patrón para encontrar 'with' statements seguidos de líneas no indentadas
    lines = content.split('\n')
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
                # Determinar la indentación correcta basada en el contexto
                # Si estamos dentro de un método (8 espacios), añadir 4 más (12 espacios)
                if line.startswith('        '):
                    corrected_line = '                ' + next_line.strip()
                else:
                    corrected_line = '                ' + next_line.strip()
                
                corrected_lines.append(corrected_line)
                print(f"  Corregida indentacion en linea {i + 1}")
        else:
            corrected_lines.append(line)
        
        i += 1
    
    # Unir las líneas
    corrected_content = '\n'.join(corrected_lines)
    
    # Escribir archivo corregido
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(corrected_content)
    
    print(f"  OK: Archivo {file_path} completamente corregido")

if __name__ == "__main__":
    print("Corrigiendo TODOS los 'with' statements...")
    fix_all_with_statements("backend/app/api/v1/endpoints/intermittent_failure_analyzer.py")
    print("Correccion completada")
