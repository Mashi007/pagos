#!/usr/bin/env python3
"""Script para verificar todos los errores en las migraciones de Alembic"""
import os
import ast
import re
import sys
from pathlib import Path

def check_syntax_errors():
    """Verificar errores de sintaxis en todas las migraciones"""
    print("=" * 80)
    print("1. VERIFICANDO ERRORES DE SINTAXIS")
    print("=" * 80)

    errors = []
    versions_dir = Path("alembic/versions")

    for file in sorted(versions_dir.glob("*.py")):
        try:
            with open(file, "r", encoding="utf-8") as f:
                ast.parse(f.read(), filename=str(file))
        except SyntaxError as e:
            errors.append(f"[ERROR] {file.name}: Línea {e.lineno}: {e.msg}")
        except Exception as e:
            errors.append(f"[ERROR] {file.name}: {str(e)}")

    if errors:
        print(f"\n[WARNING] Se encontraron {len(errors)} errores de sintaxis:\n")
        for error in errors:
            print(f"  {error}")
        return False
    else:
        print(f"\n[OK] Sin errores de sintaxis en {len(list(versions_dir.glob('*.py')))} archivos")
        return True

def check_revision_dependencies():
    """Verificar que todas las dependencias de revisiones sean válidas"""
    print("\n" + "=" * 80)
    print("2. VERIFICANDO DEPENDENCIAS DE REVISIONES")
    print("=" * 80)

    errors = []
    warnings = []
    revisions = {}
    versions_dir = Path("alembic/versions")

    # Primero, leer todas las revisiones
    for file in sorted(versions_dir.glob("*.py")):
        revision = None
        down_revision = None

        with open(file, "r", encoding="utf-8") as f:
            content = f.read()

            # Buscar revision (con o sin anotación de tipo)
            match = re.search(r"^revision(?:\s*:\s*str)?\s*=\s*['\"]([^'\"]+)['\"]", content, re.MULTILINE)
            if match:
                revision = match.group(1)

            # Buscar down_revision (con o sin anotación de tipo)
            match = re.search(r"^down_revision(?:\s*:\s*Union\[str,\s*None\])?\s*=\s*['\"]([^'\"]+)['\"]", content, re.MULTILINE)
            if match:
                down_revision = match.group(1)
            elif "down_revision" in content:
                # Buscar down_revision como tupla (para merge migrations)
                match = re.search(r"^down_revision(?:\s*:\s*Union\[str,\s*None\])?\s*=\s*\(([^)]+)\)", content, re.MULTILINE)
                if match:
                    down_revision = tuple(re.findall(r"['\"]([^'\"]+)['\"]", match.group(1)))

            if revision:
                revisions[revision] = {
                    "file": file.name,
                    "down": down_revision
                }

    # Verificar dependencias
    for rev, info in revisions.items():
        if info["down"] is None:
            warnings.append(f"[WARNING] {info['file']}: No tiene down_revision definido")
        elif isinstance(info["down"], tuple):
            # Merge migration - verificar todas las dependencias
            for dep in info["down"]:
                if dep not in revisions:
                    errors.append(f"[ERROR] {info['file']}: down_revision '{dep}' no existe")
        elif info["down"] not in revisions and info["down"] not in ["None", None]:
            errors.append(f"[ERROR] {info['file']}: down_revision '{info['down']}' no existe")

    if errors:
        print(f"\n[WARNING] Se encontraron {len(errors)} errores de dependencias:\n")
        for error in errors:
            print(f"  {error}")

    if warnings:
        print(f"\n[WARNING] Se encontraron {len(warnings)} advertencias:\n")
        for warning in warnings:
            print(f"  {warning}")

    if not errors and not warnings:
        print(f"\n[OK] Todas las {len(revisions)} migraciones tienen dependencias válidas")
        return True

    return len(errors) == 0

def check_imports():
    """Verificar que los imports necesarios estén presentes"""
    print("\n" + "=" * 80)
    print("3. VERIFICANDO IMPORTS")
    print("=" * 80)

    errors = []
    versions_dir = Path("alembic/versions")

    required_imports = {
        "op": "from alembic import op",
        "sa": "import sqlalchemy as sa",
    }

    for file in sorted(versions_dir.glob("*.py")):
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()

            # Verificar si usa op pero no lo importa
            if "op." in content and "from alembic import op" not in content:
                errors.append(f"[ERROR] {file.name}: Usa 'op' pero no lo importa")

            # Verificar si usa sa pero no lo importa
            if "sa." in content and "import sqlalchemy as sa" not in content:
                errors.append(f"[ERROR] {file.name}: Usa 'sa' pero no lo importa")

            # Verificar si usa inspect pero no lo importa
            if "inspect(" in content and "from sqlalchemy import inspect" not in content and "sa.inspect" not in content:
                if "import sqlalchemy as sa" in content:
                    pass  # OK si usa sa.inspect
                else:
                    errors.append(f"[ERROR] {file.name}: Usa 'inspect' pero no lo importa")

    if errors:
        print(f"\n[WARNING] Se encontraron {len(errors)} errores de imports:\n")
        for error in errors:
            print(f"  {error}")
        return False
    else:
        print(f"\n[OK] Todos los imports son correctos")
        return True

def check_table_operations():
    """Verificar que las operaciones de tabla verifiquen existencia"""
    print("\n" + "=" * 80)
    print("4. VERIFICANDO VERIFICACIONES DE EXISTENCIA")
    print("=" * 80)

    warnings = []
    versions_dir = Path("alembic/versions")

    operations = [
        "op.add_column",
        "op.drop_column",
        "op.alter_column",
        "op.create_index",
        "op.drop_index",
        "op.create_table",
        "op.drop_table",
        "op.create_foreign_key",
        "op.drop_constraint",
        "op.create_unique_constraint",
    ]

    for file in sorted(versions_dir.glob("*.py")):
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.split("\n")

            # Buscar operaciones sin verificaciones previas
            for i, line in enumerate(lines, 1):
                for op in operations:
                    if op in line and "upgrade()" in content[:content.find(line)]:
                        # Verificar si hay verificación antes
                        before_content = "\n".join(lines[:i])
                        if "get_table_names()" not in before_content and "get_columns()" not in before_content:
                            # Puede ser una operación segura, verificar contexto
                            if "IF EXISTS" not in line and "IF NOT EXISTS" not in line:
                                # Verificar si está dentro de un try-except
                                if "try:" not in before_content[-200:]:
                                    warnings.append(f"[WARNING] {file.name}:{i}: {op} sin verificación previa")

    if warnings:
        print(f"\n⚠️ Se encontraron {len(warnings)} posibles problemas:\n")
        for warning in warnings[:20]:  # Limitar a 20
            print(f"  {warning}")
        if len(warnings) > 20:
            print(f"  ... y {len(warnings) - 20} más")
        return False
    else:
        print(f"\n[OK] Todas las operaciones parecen tener verificaciones")
        return True

def main():
    """Ejecutar todas las verificaciones"""
    os.chdir(Path(__file__).parent)

    print("\n" + "=" * 80)
    print("VERIFICACIÓN COMPLETA DE MIGRACIONES DE ALEMBIC")
    print("=" * 80 + "\n")

    results = []

    # 1. Sintaxis
    results.append(("Sintaxis", check_syntax_errors()))

    # 2. Dependencias
    results.append(("Dependencias", check_revision_dependencies()))

    # 3. Imports
    results.append(("Imports", check_imports()))

    # 4. Verificaciones
    results.append(("Verificaciones", check_table_operations()))

    # Resumen final
    print("\n" + "=" * 80)
    print("RESUMEN FINAL")
    print("=" * 80)

    for name, result in results:
        status = "[OK] PASS" if result else "[ERROR] FAIL"
        print(f"  {status} - {name}")

    all_passed = all(result for _, result in results)

    if all_passed:
        print("\n[OK] TODAS LAS VERIFICACIONES PASARON")
        return 0
    else:
        print("\n[ERROR] ALGUNAS VERIFICACIONES FALLARON")
        return 1

if __name__ == "__main__":
    sys.exit(main())
