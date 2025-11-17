#!/usr/bin/env python3
"""
Script para corregir errores específicos restantes
Corrige errores más complejos que requieren atención manual
"""

import os
import re
from pathlib import Path

def fix_specific_errors():
    """Corregir errores específicos identificados"""

    # Lista de archivos con errores específicos y sus correcciones
    fixes = [
        {
            "file": "backend/app/core/config.py",
            "error": "closing parenthesis ')' does not match opening parenthesis '[' on line 57",
            "fix": "Revisar y corregir paréntesis/llaves no balanceados"
        },
        {
            "file": "backend/app/core/security.py",
            "error": "unmatched ')'",
            "fix": "Corregir paréntesis no balanceados"
        },
        {
            "file": "backend/app/models/__init__.py",
            "error": "'[' was never closed",
            "fix": "Cerrar corchetes abiertos"
        },
        {
            "file": "backend/app/schemas/prestamo.py",
            "error": "'[' was never closed",
            "fix": "Cerrar corchetes abiertos"
        },
        {
            "file": "backend/app/services/__init__.py",
            "error": "'[' was never closed",
            "fix": "Cerrar corchetes abiertos"
        }
    ]

    print(f"[INFO] Aplicando correcciones específicas a {len(fixes)} archivos...")

    for fix_info in fixes:
        file_path = Path(fix_info["file"])
        if file_path.exists():
            print(f"[INFO] Procesando: {fix_info['file']}")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                original_content = content

                # Aplicar correcciones específicas según el tipo de error
                if "closing parenthesis" in fix_info["error"]:
                    content = fix_unmatched_parentheses(content)
                elif "was never closed" in fix_info["error"]:
                    content = fix_unclosed_brackets(content)
                elif "unmatched" in fix_info["error"]:
                    content = fix_unmatched_brackets(content)

                if content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"[OK] Corregido: {fix_info['file']}")
                else:
                    print(f"[SKIP] Sin cambios: {fix_info['file']}")

            except Exception as e:
                print(f"[ERROR] Error en {fix_info['file']}: {e}")
        else:
            print(f"[WARN] Archivo no encontrado: {fix_info['file']}")

def fix_unmatched_parentheses(content):
    """Corregir paréntesis no balanceados"""
    lines = content.split('\n')
    fixed_lines = []

    for i, line in enumerate(lines):
        # Buscar líneas problemáticas con paréntesis
        if '(' in line and ')' not in line and not line.strip().endswith(','):
            # Si es una línea de función o método, agregar paréntesis de cierre
            if 'def ' in line or 'class ' in line:
                line = line.rstrip() + ')'
        elif '[' in line and ']' not in line and not line.strip().endswith(','):
            # Si es una línea con corchetes, agregar corchete de cierre
            if '=' in line and not line.strip().endswith(','):
                line = line.rstrip() + ']'

        fixed_lines.append(line)

    return '\n'.join(fixed_lines)

def fix_unclosed_brackets(content):
    """Corregir corchetes no cerrados"""
    lines = content.split('\n')
    fixed_lines = []

    for line in lines:
        # Buscar líneas con corchetes abiertos sin cerrar
        if '[' in line and ']' not in line:
            # Contar corchetes abiertos y cerrados
            open_count = line.count('[')
            close_count = line.count(']')
            if open_count > close_count:
                # Agregar corchetes de cierre faltantes
                missing = open_count - close_count
                line = line.rstrip() + ']' * missing

        fixed_lines.append(line)

    return '\n'.join(fixed_lines)

def fix_unmatched_brackets(content):
    """Corregir llaves y paréntesis no balanceados"""
    lines = content.split('\n')
    fixed_lines = []

    for line in lines:
        # Buscar líneas con paréntesis/llaves no balanceados
        if '(' in line and ')' not in line and not line.strip().endswith(','):
            line = line.rstrip() + ')'
        elif '{' in line and '}' not in line and not line.strip().endswith(','):
            line = line.rstrip() + '}'

        fixed_lines.append(line)

    return '\n'.join(fixed_lines)

def fix_indentation_errors():
    """Corregir errores de indentación específicos"""

    files_with_indentation = [
        "backend/app/api/v1/endpoints/concesionarios.py",
        "backend/app/api/v1/endpoints/verificar_concesionarios.py",
        "backend/app/api/v1/endpoints/intermittent_failure_analyzer.py",
        "backend/app/api/v1/endpoints/network_diagnostic.py",
        "backend/app/core/endpoint_specific_analysis.py",
        "backend/app/models/analista.py",
        "backend/app/models/concesionario.py",
        "backend/app/models/modelo_vehiculo.py",
        "backend/app/models/pago.py",
        "backend/app/schemas/conciliacion.py",
        "backend/app/schemas/kpis.py",
        "backend/app/schemas/reportes.py"
    ]

    print(f"[INFO] Corrigiendo indentación en {len(files_with_indentation)} archivos...")

    for file_path in files_with_indentation:
        path = Path(file_path)
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()

                lines = content.split('\n')
                fixed_lines = []

                for line in lines:
                    # Corregir indentación incorrecta
                    if re.match(r'^\s{1,3}[a-zA-Z_]', line) and not re.match(r'^\s{4}[a-zA-Z_]', line):
                        # Si tiene indentación incorrecta, corregir a múltiplos de 4
                        indent_match = re.match(r'^(\s+)', line)
                        if indent_match:
                            indent = indent_match.group(1)
                            if len(indent) % 4 != 0:
                                # Corregir a múltiplo de 4 más cercano
                                new_indent = ' ' * ((len(indent) // 4 + 1) * 4)
                                line = re.sub(r'^\s+', new_indent, line)

                    fixed_lines.append(line)

                if fixed_lines != lines:
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(fixed_lines))
                    print(f"[OK] Corregido indentación: {file_path}")

            except Exception as e:
                print(f"[ERROR] Error en {file_path}: {e}")

def main():
    """Función principal"""
    print("[INFO] Iniciando corrección de errores específicos...")

    fix_specific_errors()
    fix_indentation_errors()

    print("\n[OK] Corrección de errores específicos completada")
    print("[INFO] Ejecuta 'flake8 app/ --count --select=E9,F63,F7,F82' para verificar")

if __name__ == "__main__":
    main()
