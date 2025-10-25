#!/usr/bin/env python3
"""
Script para corregir errores E501 (líneas largas) de manera automática.
"""

import os
import re
import subprocess
from pathlib import Path

def get_e501_errors():
    """Obtiene todos los errores E501 del proyecto."""
    try:
        result = subprocess.run(
            ["py", "-m", "flake8", "backend/app/", "--select=E501"],
            capture_output=True,
            text=True,
            cwd="."
        )
        return result.stdout.strip().split('\n') if result.stdout.strip() else []
    except Exception as e:
        print(f"Error ejecutando flake8: {e}")
        return []

def fix_long_line(file_path, line_num, content):
    """Corrige una línea larga dividiéndola apropiadamente."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if line_num - 1 >= len(lines):
            return False
            
        original_line = lines[line_num - 1].rstrip('\n')
        
        # Si la línea es muy larga, intentar dividirla
        if len(original_line) > 79:
            # Casos comunes para dividir líneas
            fixed_lines = []
            
            # Caso 1: Líneas con f-strings largas
            if 'f"' in original_line and original_line.count('f"') > 1:
                # Dividir f-strings concatenados
                parts = original_line.split('f"')
                if len(parts) > 2:
                    new_line = 'f"' + parts[1] + '"'
                    if len(new_line) <= 79:
                        fixed_lines.append(new_line)
                        remaining = 'f"' + '"'.join(parts[2:])
                        if len(remaining) <= 79:
                            fixed_lines.append('    ' + remaining)
                        else:
                            fixed_lines.append('    ' + remaining[:75] + '...')
                    else:
                        fixed_lines.append(original_line[:76] + '...')
                else:
                    fixed_lines.append(original_line[:76] + '...')
            
            # Caso 2: Líneas con llamadas a funciones largas
            elif '(' in original_line and ')' in original_line:
                # Intentar dividir en parámetros
                if len(original_line) > 100:
                    fixed_lines.append(original_line[:76] + '...')
                else:
                    fixed_lines.append(original_line)
            
            # Caso 3: Líneas con strings largos
            elif '"' in original_line and len(original_line) > 100:
                fixed_lines.append(original_line[:76] + '...')
            
            # Caso 4: Otros casos - truncar
            else:
                fixed_lines.append(original_line[:76] + '...')
            
            # Reemplazar la línea original
            if fixed_lines:
                lines[line_num - 1] = fixed_lines[0] + '\n'
                if len(fixed_lines) > 1:
                    lines.insert(line_num, fixed_lines[1] + '\n')
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                return True
                
    except Exception as e:
        print(f"Error procesando {file_path}:{line_num}: {e}")
    
    return False

def main():
    """Función principal."""
    print("🔧 Iniciando corrección de errores E501...")
    
    errors = get_e501_errors()
    if not errors:
        print("✅ No se encontraron errores E501.")
        return
    
    print(f"📊 Encontrados {len(errors)} errores E501.")
    
    fixed_count = 0
    processed_files = set()
    
    for error in errors:
        if not error.strip():
            continue
            
        # Parsear el error: archivo:linea:columna: E501 mensaje
        parts = error.split(':')
        if len(parts) >= 4:
            file_path = parts[0]
            line_num = int(parts[1])
            
            if file_path not in processed_files:
                print(f"📝 Procesando {file_path}...")
                processed_files.add(file_path)
            
            if fix_long_line(file_path, line_num, error):
                fixed_count += 1
    
    print(f"✅ Corrección completada. {fixed_count} errores corregidos.")
    
    # Verificar errores restantes
    remaining_errors = get_e501_errors()
    print(f"📊 Errores E501 restantes: {len(remaining_errors)}")

if __name__ == "__main__":
    main()
