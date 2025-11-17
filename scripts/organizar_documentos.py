#!/usr/bin/env python3
"""
Script para organizar automáticamente archivos .md en carpetas correspondientes
Uso: python scripts/organizar_documentos.py [--dry-run]
"""

import os
import sys
import argparse
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

# Colores para output (ANSI)
class Colors:
    INFO = '\033[96m'
    SUCCESS = '\033[92m'
    WARNING = '\033[93m'
    ERROR = '\033[91m'
    RESET = '\033[0m'

# Definir reglas de clasificación
RULES: Dict[str, str] = {
    # Auditorías
    "AUDITORIA": "Documentos/Auditorias",

    # Análisis
    "ANALISIS": "Documentos/Analisis",

    # Testing
    "TEST_": "Documentos/Testing",
    "CI-CD": "Documentos/Testing",
    "ACCESIBILIDAD": "Documentos/Testing",

    # Configuración e Instalación
    "INSTALAR": "Documentos/Configuracion",
    "COMANDOS_INSTALACION": "Documentos/Configuracion",
    "PASOS_INSTALACION": "Documentos/Configuracion",
    "DEPLOYMENT": "Documentos/Configuracion",
    "VERIFICAR_INSTALACION": "Documentos/Configuracion",

    # Desarrollo
    "PROCEDIMIENTO": "Documentos/Desarrollo",
    "AVANCE": "Documentos/Desarrollo",
    "ESTADO_FINAL": "Documentos/Desarrollo",
    "ESTADO_CLIENTES": "Documentos/Desarrollo",
    "RESUMEN_CAMBIOS": "Documentos/Desarrollo",
    "RESUMEN_ERRORES": "Documentos/Desarrollo",
    "PROPUESTA": "Documentos/Desarrollo",

    # General (verificaciones, confirmaciones, soluciones, etc.)
    "VERIFICACION": "Documentos/General",
    "CONFIRMACION": "Documentos/General",
    "CHECKLIST": "Documentos/General",
    "SOLUCION": "Documentos/General",
    "CORRECCION": "Documentos/General",
    "CONEXIONES": "Documentos/General",
    "EXPORTACION": "Documentos/General",
    "SISTEMA_NOTIFICACIONES": "Documentos/General",
    "RESUMEN_NOTIFICACIONES": "Documentos/General",
    "GUIA": "Documentos/General",
    "ESCALA": "Documentos/General",
    "DETALLE": "Documentos/General",
    "EXPLICACION": "Documentos/General",
    "ACLARACION": "Documentos/General",
    "CAMBIO_IMPORTANTE": "Documentos/General",
}

# Carpetas que deben mantenerse en su ubicación actual
EXCLUDED_FOLDERS: List[str] = [
    "Documentos",
    "backend",
    "frontend",
    "scripts",
    "node_modules",
    ".git",
]

# Archivos que no deben moverse
EXCLUDED_FILES: List[str] = [
    "README.md",
]


def get_destination_folder(filename: str) -> str:
    """Determina la carpeta destino basada en el nombre del archivo."""
    filename_upper = filename.upper().replace(".MD", "")

    # Verificar cada regla
    for pattern, folder in RULES.items():
        if pattern in filename_upper:
            return folder

    # Si no coincide con ninguna regla, mantener en General
    return "Documentos/General"


def should_process_file(file_path: Path, filename: str, root_path: Path) -> bool:
    """Verifica si el archivo debe ser procesado."""
    # Verificar si está en carpeta excluida
    relative_path = file_path.relative_to(root_path)
    path_parts = relative_path.parts

    for excluded in EXCLUDED_FOLDERS:
        if excluded in path_parts:
            return False

    # Verificar si el archivo está excluido
    if filename in EXCLUDED_FILES:
        return False

    # Solo procesar archivos .md
    if not filename.lower().endswith('.md'):
        return False

    return True


def organize_documents(root_path: Path, dry_run: bool = False) -> Tuple[int, int, int]:
    """Organiza los documentos .md según las reglas definidas."""
    print(f"\n{Colors.INFO}📁 ORGANIZADOR DE DOCUMENTOS MARKDOWN{Colors.RESET}\n")

    moved = 0
    skipped = 0
    errors = 0

    # Buscar todos los archivos .md
    print(f"{Colors.INFO}🔍 Buscando archivos .md...{Colors.RESET}")

    md_files = []
    for md_file in root_path.rglob("*.md"):
        if should_process_file(md_file, md_file.name, root_path):
            md_files.append(md_file)

    print(f"   Encontrados: {len(md_files)} archivos\n")

    # Procesar cada archivo
    for file_path in md_files:
        filename = file_path.name

        # Determinar carpeta destino
        destination_folder = Path(root_path) / get_destination_folder(filename)
        destination_file = destination_folder / filename

        # Verificar si ya está en la carpeta correcta
        current_folder = file_path.parent.relative_to(root_path)
        if str(current_folder) == str(destination_folder.relative_to(root_path)):
            print(f"{Colors.SUCCESS}✓ {filename}{Colors.RESET}")
            print(f"   Ya está en: {destination_folder.relative_to(root_path)}")
            skipped += 1
            continue

        # Verificar si el archivo destino ya existe
        if destination_file.exists():
            print(f"{Colors.WARNING}⚠ {filename}{Colors.RESET}")
            print(f"   Ya existe en destino: {destination_folder.relative_to(root_path)}")
            skipped += 1
            continue

        # Crear carpeta destino si no existe
        if not destination_folder.exists():
            if not dry_run:
                destination_folder.mkdir(parents=True, exist_ok=True)
                print(f"{Colors.INFO}📁 Carpeta creada: {destination_folder.relative_to(root_path)}{Colors.RESET}")

        # Mover archivo
        if dry_run:
            print(f"{Colors.WARNING}📋 [DRY RUN] Movería:{Colors.RESET}")
            print(f"   De: {file_path.relative_to(root_path)}")
            print(f"   A:  {destination_file.relative_to(root_path)}")
            moved += 1
        else:
            try:
                shutil.move(str(file_path), str(destination_file))
                print(f"{Colors.SUCCESS}✓ {filename}{Colors.RESET}")
                print(f"   Movido: {file_path.relative_to(root_path)} → {destination_folder.relative_to(root_path)}/")
                moved += 1
            except Exception as e:
                print(f"{Colors.ERROR}✗ Error moviendo {filename}: {e}{Colors.RESET}")
                errors += 1

    return moved, skipped, errors


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Organiza archivos .md en carpetas correspondientes"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo muestra lo que haría sin mover archivos"
    )
    parser.add_argument(
        "--root",
        type=str,
        default=".",
        help="Ruta raíz del proyecto (default: .)"
    )

    args = parser.parse_args()

    root_path = Path(args.root).resolve()

    if not root_path.exists():
        print(f"{Colors.ERROR}✗ Error: La ruta {root_path} no existe{Colors.RESET}")
        sys.exit(1)

    moved, skipped, errors = organize_documents(root_path, args.dry_run)

    # Resumen
    print(f"\n{Colors.INFO}═══════════════════════════════════════{Colors.RESET}")
    print(f"{Colors.INFO}📊 RESUMEN{Colors.RESET}")
    print(f"{Colors.INFO}═══════════════════════════════════════{Colors.RESET}")

    if args.dry_run:
        print(f"   Archivos a mover: {Colors.WARNING}{moved}{Colors.RESET}")
    else:
        print(f"   Archivos movidos: {Colors.SUCCESS}{moved}{Colors.RESET}")

    print(f"   Archivos omitidos: {Colors.INFO}{skipped}{Colors.RESET}")

    if errors > 0:
        print(f"   Errores: {Colors.ERROR}{errors}{Colors.RESET}")

    print(f"\n{Colors.SUCCESS}✅ Proceso completado{Colors.RESET}\n")


if __name__ == "__main__":
    main()

