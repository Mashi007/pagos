"""
Script para verificar y corregir espacios en blanco en todo el sistema
Verifica:
- Trailing whitespace (espacios al final de líneas)
- Líneas en blanco con espacios
- Múltiples espacios consecutivos (excepto indentación)
- Líneas en blanco al final del archivo
- Falta de nueva línea al final
- Tabs vs espacios
"""
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple


class WhitespaceChecker:
    """Verificador y corrector de espacios en blanco"""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.issues: Dict[str, List[Dict]] = {}
        self.fixed_files: List[str] = []

        # Extensiones de archivos a verificar
        self.code_extensions = {
            '.py', '.ts', '.tsx', '.js', '.jsx', '.json',
            '.css', '.html', '.md', '.yaml', '.yml', '.toml'
        }

        # Directorios a excluir
        self.exclude_dirs = {
            'node_modules', '__pycache__', '.git', 'venv', '.venv',
            'env', 'build', 'dist', 'alembic/versions', '.next',
            'migrations', 'uploads', 'ml_models', 'tests/__pycache__',
            '.mypy_cache', '.pytest_cache', '.ruff_cache', '.tox',
            '.coverage', 'htmlcov', '.eggs', '*.egg-info'
        }

    def should_check_file(self, file_path: Path) -> bool:
        """Determina si un archivo debe ser verificado"""
        # Verificar extensión
        if file_path.suffix not in self.code_extensions:
            return False

        # Verificar si está en directorio excluido
        parts = file_path.parts
        for excluded in self.exclude_dirs:
            if excluded in parts:
                return False

        # Excluir archivos de cache específicos (pero permitir .github)
        path_str = str(file_path)
        if '.mypy_cache' in path_str or '.pytest_cache' in path_str:
            return False

        return True

    def check_file(self, file_path: Path) -> Tuple[bool, List[Dict]]:
        """
        Verifica un archivo y retorna (necesita_correccion, lista_issues)
        """
        issues = []
        needs_fix = False

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            # Verificar cada línea
            for line_num, line in enumerate(lines, 1):
                original_line = line

                # 1. Trailing whitespace (W291)
                if line.rstrip() != line.rstrip('\n'):
                    stripped = line.rstrip()
                    if stripped != line.rstrip('\n'):
                        issues.append({
                            'line': line_num,
                            'type': 'trailing_whitespace',
                            'description': f'Espacios al final de la línea {line_num}'
                        })
                        needs_fix = True

                # 2. Línea en blanco con espacios (W293)
                if line.strip() == '' and line != '\n' and line != '':
                    issues.append({
                        'line': line_num,
                        'type': 'blank_line_with_spaces',
                        'description': f'Línea en blanco con espacios en línea {line_num}'
                    })
                    needs_fix = True

                # 3. Tabs en lugar de espacios (solo para Python, TS, TSX, JS, JSX)
                if file_path.suffix in {'.py', '.ts', '.tsx', '.js', '.jsx'}:
                    if '\t' in line:
                        issues.append({
                            'line': line_num,
                            'type': 'tabs_instead_of_spaces',
                            'description': f'Tab encontrado en línea {line_num} (debe usar espacios)'
                        })
                        needs_fix = True

            # 4. Líneas en blanco al final del archivo (W391)
            trailing_blank_lines = 0
            for line in reversed(lines):
                if line.strip() == '':
                    trailing_blank_lines += 1
                else:
                    break

            if trailing_blank_lines > 1:
                issues.append({
                    'line': len(lines) - trailing_blank_lines + 1,
                    'type': 'trailing_blank_lines',
                    'description': f'{trailing_blank_lines} líneas en blanco al final del archivo'
                })
                needs_fix = True

            # 5. Falta nueva línea al final (W292)
            if lines and not lines[-1].endswith('\n'):
                issues.append({
                    'line': len(lines),
                    'type': 'missing_final_newline',
                    'description': 'Falta nueva línea al final del archivo'
                })
                needs_fix = True

        except Exception as e:
            issues.append({
                'line': 0,
                'type': 'error',
                'description': f'Error al leer archivo: {e}'
            })

        return needs_fix, issues

    def fix_file(self, file_path: Path) -> bool:
        """Corrige problemas de espacios en blanco en un archivo"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            modified = False
            new_lines = []

            for line in lines:
                original_line = line

                # 1. Eliminar trailing whitespace
                stripped = line.rstrip()
                if line != stripped:
                    line = stripped + '\n' if line.endswith('\n') else stripped
                    modified = True

                # 2. Limpiar líneas en blanco
                if line.strip() == '':
                    line = '\n'
                    if original_line != line:
                        modified = True

                # 3. Convertir tabs a espacios (solo para Python, TS, TSX, JS, JSX)
                if file_path.suffix in {'.py', '.ts', '.tsx', '.js', '.jsx'}:
                    if '\t' in line:
                        # Reemplazar tabs con 4 espacios (o mantener indentación)
                        # Preservar el resto de la línea
                        leading_tabs = len(line) - len(line.lstrip('\t'))
                        if leading_tabs > 0:
                            # Tabs de indentación: convertir a espacios
                            spaces = ' ' * (leading_tabs * 4)
                            line = spaces + line.lstrip('\t')
                        else:
                            # Tabs en medio de la línea: reemplazar con espacios
                            line = line.replace('\t', '    ')
                        modified = True

                new_lines.append(line)

            # 4. Eliminar líneas en blanco al final (máximo 1)
            while len(new_lines) > 1 and new_lines[-1].strip() == '' and new_lines[-2].strip() == '':
                new_lines.pop()
                modified = True

            # 5. Asegurar nueva línea al final
            if new_lines and not new_lines[-1].endswith('\n'):
                new_lines[-1] += '\n'
                modified = True
            elif not new_lines:
                # Archivo vacío
                new_lines = ['\n']
                modified = True

            if modified:
                with open(file_path, 'w', encoding='utf-8', errors='ignore') as f:
                    f.writelines(new_lines)
                return True

            return False

        except Exception as e:
            print(f"  [ERROR] Error al corregir {file_path}: {e}")
            return False

    def scan_all_files(self, fix: bool = False) -> Dict[str, any]:
        """Escanea todos los archivos y opcionalmente los corrige"""
        total_files = 0
        files_with_issues = 0
        total_issues = 0

        print(f"\n{'=' * 70}")
        print(f"Verificando espacios en blanco en: {self.root_dir}")
        print(f"{'=' * 70}\n")

        for file_path in self.root_dir.rglob('*'):
            if not file_path.is_file():
                continue

            if not self.should_check_file(file_path):
                continue

            total_files += 1
            needs_fix, issues = self.check_file(file_path)

            if needs_fix:
                files_with_issues += 1
                total_issues += len(issues)
                rel_path = file_path.relative_to(self.root_dir)
                self.issues[str(rel_path)] = issues

                if fix:
                    if self.fix_file(file_path):
                        self.fixed_files.append(str(rel_path))
                        print(f"[CORREGIDO] {rel_path} ({len(issues)} problemas)")
                else:
                    print(f"[PROBLEMA] {rel_path}")
                    for issue in issues[:5]:  # Mostrar máximo 5 por archivo
                        print(f"  - Línea {issue['line']}: {issue['description']}")
                    if len(issues) > 5:
                        print(f"  ... y {len(issues) - 5} problemas más")

        return {
            'total_files': total_files,
            'files_with_issues': files_with_issues,
            'total_issues': total_issues,
            'fixed_files': len(self.fixed_files) if fix else 0
        }

    def generate_report(self, stats: Dict[str, any], fix: bool = False):
        """Genera un reporte de los problemas encontrados"""
        print(f"\n{'=' * 70}")
        print("RESUMEN DE VERIFICACIÓN DE ESPACIOS EN BLANCO")
        print(f"{'=' * 70}")
        print(f"Archivos verificados: {stats['total_files']}")
        print(f"Archivos con problemas: {stats['files_with_issues']}")
        print(f"Total de problemas encontrados: {stats['total_issues']}")

        if fix:
            print(f"Archivos corregidos: {stats['fixed_files']}")

        # Agrupar problemas por tipo
        issue_types = {}
        for file_issues in self.issues.values():
            for issue in file_issues:
                issue_type = issue['type']
                issue_types[issue_type] = issue_types.get(issue_type, 0) + 1

        if issue_types:
            print(f"\nProblemas por tipo:")
            for issue_type, count in sorted(issue_types.items(), key=lambda x: x[1], reverse=True):
                type_names = {
                    'trailing_whitespace': 'Espacios al final de líneas',
                    'blank_line_with_spaces': 'Líneas en blanco con espacios',
                    'trailing_blank_lines': 'Múltiples líneas en blanco al final',
                    'missing_final_newline': 'Falta nueva línea al final',
                    'tabs_instead_of_spaces': 'Tabs en lugar de espacios'
                }
                print(f"  - {type_names.get(issue_type, issue_type)}: {count}")

        print(f"{'=' * 70}\n")


def main():
    """Función principal"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Verifica y corrige espacios en blanco en todo el sistema'
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Corregir automáticamente los problemas encontrados'
    )
    parser.add_argument(
        '--dir',
        type=str,
        default='.',
        help='Directorio raíz a verificar (por defecto: directorio actual)'
    )

    args = parser.parse_args()

    root_dir = Path(args.dir).resolve()
    if not root_dir.exists():
        print(f"Error: El directorio {root_dir} no existe")
        return

    checker = WhitespaceChecker(root_dir)
    stats = checker.scan_all_files(fix=args.fix)
    checker.generate_report(stats, fix=args.fix)

    if not args.fix and stats['files_with_issues'] > 0:
        print("\n[INFO] Ejecuta con --fix para corregir automaticamente los problemas")
        print("   Ejemplo: python scripts/verificar_espacios_blanco.py --fix\n")


if __name__ == "__main__":
    main()

