#!/usr/bin/env python3
"""
Script para identificar textualmente el patrón "tiene 8 espacios, pero debería tener 4 espacios"
"""

import os
import re

def analyze_indentation_patterns(file_path):
    """Analizar patrones de indentación en un archivo específico"""
    
    print(f"Analizando patrones de indentacion en {file_path}")
    
    if not os.path.exists(file_path):
        print(f"  ERROR: Archivo no encontrado: {file_path}")
        return
    
    # Leer archivo
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    issues_found = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        line_num = i + 1
        
        # Detectar líneas que empiecen con 8 espacios pero deberían tener 4
        if line.startswith('        ') and not line.startswith('            '):
            stripped = line.strip()
            
            # Si es un método o función, probablemente debería tener 4 espacios
            if stripped.startswith('def ') or stripped.startswith('class '):
                # Verificar el contexto anterior
                context_before = []
                for j in range(max(0, i-5), i):
                    if lines[j].strip():
                        context_before.append(f"  {j+1:3d}: {lines[j].rstrip()}")
                
                # Verificar si estamos dentro de una clase
                in_class = False
                for j in range(i-1, -1, -1):
                    if lines[j].strip().startswith('class '):
                        in_class = True
                        break
                    elif lines[j].strip().startswith('def ') and not lines[j].startswith('        '):
                        break
                
                if in_class:
                    issue = {
                        'line': line_num,
                        'content': stripped,
                        'current_indent': 8,
                        'expected_indent': 4,
                        'type': 'method_in_class',
                        'context': context_before[-3:] if context_before else []
                    }
                    issues_found.append(issue)
                    print(f"  ERROR: Linea {line_num}: {stripped}")
                    print(f"     Tiene 8 espacios, pero deberia tener 4 espacios (metodo en clase)")
        
        # Detectar líneas que empiecen con 4 espacios pero deberían tener 8
        elif line.startswith('    ') and not line.startswith('        '):
            stripped = line.strip()
            
            # Si es un método o función, probablemente debería tener 8 espacios
            if stripped.startswith('def ') or stripped.startswith('class '):
                # Verificar el contexto anterior
                context_before = []
                for j in range(max(0, i-5), i):
                    if lines[j].strip():
                        context_before.append(f"  {j+1:3d}: {lines[j].rstrip()}")
                
                # Verificar si estamos dentro de una clase
                in_class = False
                for j in range(i-1, -1, -1):
                    if lines[j].strip().startswith('class '):
                        in_class = True
                        break
                    elif lines[j].strip().startswith('def ') and not lines[j].startswith('        '):
                        break
                
                if in_class:
                    issue = {
                        'line': line_num,
                        'content': stripped,
                        'current_indent': 4,
                        'expected_indent': 8,
                        'type': 'method_in_class',
                        'context': context_before[-3:] if context_before else []
                    }
                    issues_found.append(issue)
                    print(f"  ERROR: Linea {line_num}: {stripped}")
                    print(f"     Tiene 4 espacios, pero deberia tener 8 espacios (metodo en clase)")
        
        i += 1
    
    # Mostrar resumen
    if issues_found:
        print(f"\n  RESUMEN: Problemas encontrados:")
        print(f"     Total de problemas: {len(issues_found)}")
        
        # Agrupar por tipo
        by_type = {}
        for issue in issues_found:
            key = f"{issue['current_indent']} -> {issue['expected_indent']} espacios"
            if key not in by_type:
                by_type[key] = []
            by_type[key].append(issue)
        
        for indent_type, issues in by_type.items():
            print(f"     {indent_type}: {len(issues)} problemas")
    else:
        print(f"  RESUMEN: No se encontraron problemas de indentacion")
    
    return issues_found

def fix_indentation_issues(file_path, issues):
    """Corregir los problemas de indentación identificados"""
    
    if not issues:
        print(f"  OK: No hay problemas que corregir en {file_path}")
        return
    
    print(f"\nCorrigiendo {len(issues)} problemas en {file_path}")
    
    # Leer archivo
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Corregir cada problema
    for issue in issues:
        line_num = issue['line'] - 1  # Convertir a índice 0-based
        if line_num < len(lines):
            original_line = lines[line_num]
            stripped = original_line.strip()
            
            if issue['expected_indent'] == 4:
                # Corregir a 4 espacios
                corrected_line = '    ' + stripped + '\n'
            elif issue['expected_indent'] == 8:
                # Corregir a 8 espacios
                corrected_line = '        ' + stripped + '\n'
            else:
                continue
            
            lines[line_num] = corrected_line
            print(f"  CORREGIDO: Linea {issue['line']}: {stripped}")
    
    # Escribir archivo corregido
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print(f"  OK: Archivo {file_path} corregido")

def analyze_all_files():
    """Analizar todos los archivos con problemas de indentación"""
    
    files_to_analyze = [
        "backend/app/api/v1/endpoints/critical_error_monitor.py",
        "backend/app/api/v1/endpoints/intermittent_failure_analyzer.py", 
        "backend/app/api/v1/endpoints/network_diagnostic.py",
        "backend/app/api/v1/endpoints/temporal_analysis.py"
    ]
    
    all_issues = {}
    
    for file_path in files_to_analyze:
        issues = analyze_indentation_patterns(file_path)
        if issues:
            all_issues[file_path] = issues
        print()
    
    # Mostrar resumen general
    total_issues = sum(len(issues) for issues in all_issues.values())
    if total_issues > 0:
        print(f"RESUMEN GENERAL:")
        print(f"   Total de archivos con problemas: {len(all_issues)}")
        print(f"   Total de problemas encontrados: {total_issues}")
        
        for file_path, issues in all_issues.items():
            print(f"   {file_path}: {len(issues)} problemas")
        
        # Preguntar si corregir
        print(f"\n¿Deseas corregir automaticamente estos problemas? (y/n): ", end="")
        response = input().lower().strip()
        
        if response == 'y' or response == 'yes':
            for file_path, issues in all_issues.items():
                fix_indentation_issues(file_path, issues)
            print(f"\nOK: Todos los problemas han sido corregidos")
        else:
            print(f"\nCANCELADO: Correccion cancelada")
    else:
        print(f"OK: No se encontraron problemas de indentacion en ningun archivo")

if __name__ == "__main__":
    print("Analizando patrones de indentacion...")
    analyze_all_files()
    print("Analisis completado")
