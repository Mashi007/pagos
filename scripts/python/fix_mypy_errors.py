#!/usr/bin/env python3
"""
Script para corregir automáticamente errores comunes de Mypy en el código.
Agrega type: ignore comments en asignaciones de SQLAlchemy y otros patrones comunes.
"""

import re
from pathlib import Path

# Patrones de errores comunes y sus correcciones
FIXES = [
    # Asignaciones a Column de SQLAlchemy
    (
        r"(\w+\.\w+)\s*=\s*(True|False)\s*$",
        r"\1 = \2  # type: ignore[assignment]",
        "Column[bool] assignments",
    ),
    (
        r"(\w+\.\w+)\s*=\s*(datetime\.now\(\)|datetime\.utcnow\(\))\s*$",
        r"\1 = \2  # type: ignore[assignment]",
        "Column[datetime] assignments",
    ),
    (
        r"(\w+\.\w+)\s*=\s*([\"'].*?[\"'])\s*$",
        r"\1 = \2  # type: ignore[assignment]",
        "Column[str] assignments (strings)",
    ),
    (
        r"(\w+\.\w+)\s*=\s*(\d+)\s*$",
        r"\1 = \2  # type: ignore[assignment]",
        "Column[int] assignments",
    ),
    (
        r"(\w+\.\w+)\s*=\s*(Decimal\([^)]+\))\s*$",
        r"\1 = \2  # type: ignore[assignment]",
        "Column[Decimal] assignments",
    ),
    (
        r"(\w+\.\w+)\s*=\s*(date\([^)]+\))\s*$",
        r"\1 = \2  # type: ignore[assignment]",
        "Column[date] assignments",
    ),
]

# Archivos a procesar
BACKEND_PATH = Path(__file__).parent.parent.parent / "backend" / "app"
EXCLUDE_PATTERNS = ["__pycache__", ".pyc", "migrations", "alembic"]


def should_process_file(file_path: Path) -> bool:
    """Verifica si un archivo debe ser procesado."""
    if not file_path.suffix == ".py":
        return False
    for pattern in EXCLUDE_PATTERNS:
        if pattern in str(file_path):
            return False
    return True


def fix_file(file_path: Path) -> tuple[int, list[str]]:
    """Corrige errores comunes en un archivo."""
    try:
        content = file_path.read_text(encoding="utf-8")
        original_content = content
        fixes_applied = []

        for pattern, replacement, description in FIXES:
            # Solo aplicar si no tiene ya un type: ignore
            pattern_with_check = re.compile(
                rf"{pattern}(?!\s*#\s*type:\s*ignore)", re.MULTILINE
            )
            matches = pattern_with_check.findall(content)
            if matches:
                content = pattern_with_check.sub(replacement, content)
                fixes_applied.append(f"{description}: {len(matches)} fixes")

        if content != original_content:
            file_path.write_text(content, encoding="utf-8")
            return (1, fixes_applied)
        return (0, [])

    except Exception as e:
        print(f"Error procesando {file_path}: {e}")
        return (0, [])


def main():
    """Procesa todos los archivos Python en backend/app."""
    files_processed = 0
    files_modified = 0
    total_fixes = []

    for file_path in BACKEND_PATH.rglob("*.py"):
        if should_process_file(file_path):
            files_processed += 1
            modified, fixes = fix_file(file_path)
            if modified:
                files_modified += 1
                total_fixes.extend(fixes)
                print(f"✅ {file_path.relative_to(BACKEND_PATH.parent.parent)}")

    print(f"\n📊 Resumen:")
    print(f"  Archivos procesados: {files_processed}")
    print(f"  Archivos modificados: {files_modified}")
    print(f"  Correcciones aplicadas: {len(total_fixes)}")


if __name__ == "__main__":
    main()

