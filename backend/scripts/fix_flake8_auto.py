"""
Script para corregir automáticamente errores simples de flake8
Corrige: W293, W291, W391, W292
"""
import os
import re
from pathlib import Path


def fix_file(file_path: Path) -> bool:
    """Corrige errores simples de formato en un archivo"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        modified = False
        new_lines = []

        for i, line in enumerate(lines):
            original_line = line

            # W293: Eliminar espacios en líneas en blanco
            if line.strip() == '':
                line = '\n'
                if original_line != line:
                    modified = True

            # W291: Eliminar trailing whitespace
            stripped = line.rstrip()
            if line != stripped:
                line = stripped + '\n' if line.endswith('\n') else stripped
                modified = True

            new_lines.append(line)

        # W391: Eliminar líneas en blanco al final del archivo
        while new_lines and new_lines[-1].strip() == '':
            new_lines.pop()
            modified = True

        # W292: Agregar nueva línea al final si falta
        if new_lines and not new_lines[-1].endswith('\n'):
            new_lines[-1] += '\n'
            modified = True
        elif not new_lines:
            # Archivo vacío, agregar solo nueva línea
            new_lines = ['\n']
            modified = True

        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            return True

        return False
    except Exception as e:
        print(f"Error procesando {file_path}: {e}")
        return False


def main():
    """Corrige errores automáticos en todos los archivos Python"""
    backend_dir = Path(__file__).parent.parent
    exclude_dirs = {
        'migrations', '__pycache__', '.git', 'venv', '.venv',
        'env', 'node_modules', 'build', 'dist', 'alembic/versions'
    }

    fixed_count = 0
    total_count = 0

    for py_file in backend_dir.rglob('*.py'):
        # Verificar si está en directorio excluido
        parts = py_file.parts
        if any(excluded in parts for excluded in exclude_dirs):
            continue

        total_count += 1
        if fix_file(py_file):
            fixed_count += 1
            print(f"[OK] Corregido: {py_file.relative_to(backend_dir)}")

    print(f"\n{'='*60}")
    print(f"Archivos procesados: {total_count}")
    print(f"Archivos corregidos: {fixed_count}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
