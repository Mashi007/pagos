#!/usr/bin/env python3
"""
Script para corregir todos los errores de indentación en intermittent_failure_analyzer.py
"""

def fix_intermittent_failure_analyzer():
    """Corregir errores de indentación en intermittent_failure_analyzer.py"""
    
    file_path = "backend/app/api/v1/endpoints/intermittent_failure_analyzer.py"
    
    print(f"Corrigiendo {file_path}")
    
    # Leer archivo
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Corregir métodos mal indentados
    corrected_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Detectar métodos que están mal indentados (4 espacios en lugar de 8)
        if (line.strip().startswith('def ') and 
            line.startswith('    ') and 
            not line.startswith('        ') and
            i > 0 and 
            lines[i-1].strip() and 
            not lines[i-1].strip().startswith('#')):
            
            # Es un método mal indentado, corregirlo
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

if __name__ == "__main__":
    print("Corrigiendo errores de indentacion en intermittent_failure_analyzer.py...")
    fix_intermittent_failure_analyzer()
    print("Correccion completada")
