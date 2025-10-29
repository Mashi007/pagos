#!/usr/bin/env python3
"""
Script para organizar todos los archivos .sql en una carpeta centralizada
Uso: python scripts/organizar_sql.py [--dry-run] [--target-folder scripts/sql]
"""

import os
import sys
import argparse
import shutil
from pathlib import Path
from typing import List, Tuple

# Colores para output (ANSI)
class Colors:
    INFO = '\033[96m'
    SUCCESS = '\033[92m'
    WARNING = '\033[93m'
    ERROR = '\033[91m'
    RESET = '\033[0m'

# Carpetas que deben mantenerse en su ubicación actual
EXCLUDED_FOLDERS: List[str] = [
    "node_modules",
    ".git",
    "migrations",  # Mantener migrations en su lugar
]

# Patrones de archivos que no deben moverse (pueden ser migraciones automáticas)
EXCLUDED_PATTERNS: List[str] = [
    "*migration*.sql",
    "*migrations*.sql",
]


def should_process_file(file_path: Path, root_path: Path) -> bool:
    """Verifica si el archivo debe ser procesado."""
    relative_path = file_path.relative_to(root_path)
    path_parts = relative_path.parts
    
    # Verificar si está en carpeta excluida
    for excluded in EXCLUDED_FOLDERS:
        if excluded in path_parts:
            return False
    
    # Verificar patrones excluidos
    for pattern in EXCLUDED_PATTERNS:
        if file_path.name.lower().startswith(pattern.replace("*", "").lower()) or \
           pattern.replace("*", "").lower() in file_path.name.lower():
            return False
    
    return True


def organize_sql_files(root_path: Path, target_folder: str, dry_run: bool = False) -> Tuple[int, int, int, int]:
    """Organiza los archivos .sql en una carpeta centralizada."""
    print(f"\n{Colors.INFO}ORGANIZADOR DE ARCHIVOS SQL{Colors.RESET}\n")
    
    moved = 0
    skipped = 0
    errors = 0
    conflicts = 0
    
    # Buscar todos los archivos .sql
    print(f"{Colors.INFO}Buscando archivos .sql...{Colors.RESET}")
    
    sql_files = []
    for sql_file in root_path.rglob("*.sql"):
        if should_process_file(sql_file, root_path):
            sql_files.append(sql_file)
    
    print(f"   Encontrados: {len(sql_files)} archivos\n")
    
    if len(sql_files) == 0:
        print(f"{Colors.WARNING}No se encontraron archivos SQL para organizar.{Colors.RESET}\n")
        return 0, 0, 0, 0
    
    # Crear carpeta destino
    destination_path = root_path / target_folder
    
    if not destination_path.exists():
        if not dry_run:
            destination_path.mkdir(parents=True, exist_ok=True)
            print(f"{Colors.INFO}[INFO] Carpeta creada: {target_folder}{Colors.RESET}")
        else:
            print(f"{Colors.WARNING}[DRY RUN] Crearía carpeta: {target_folder}{Colors.RESET}")
    
    # Procesar cada archivo
    for file_path in sql_files:
        filename = file_path.name
        destination_file = destination_path / filename
        
        # Verificar si ya está en la carpeta destino
        current_folder = file_path.parent.relative_to(root_path)
        if str(current_folder) == target_folder:
            print(f"{Colors.SUCCESS}[OK] {filename} ya está en: {target_folder}{Colors.RESET}")
            skipped += 1
            continue
        
        # Verificar si el archivo destino ya existe
        if destination_file.exists():
            # Si es el mismo archivo, no hacer nada
            if file_path.resolve() == destination_file.resolve():
                print(f"{Colors.SUCCESS}[OK] {filename} ya está en destino{Colors.RESET}")
                skipped += 1
                continue
            
            # Si hay conflicto de nombres, crear nombre único
            base_name = destination_file.stem
            extension = destination_file.suffix
            counter = 1
            new_filename = f"{base_name}_{counter}{extension}"
            destination_file = destination_path / new_filename
            
            while destination_file.exists():
                counter += 1
                new_filename = f"{base_name}_{counter}{extension}"
                destination_file = destination_path / new_filename
            
            print(f"{Colors.WARNING}[WARN] {filename} tiene conflicto, se renombrará a: {new_filename}{Colors.RESET}")
            filename = new_filename
            conflicts += 1
        
        # Mover archivo
        if dry_run:
            print(f"{Colors.WARNING}[DRY RUN] Movería:{Colors.RESET}")
            print(f"   De: {file_path.relative_to(root_path)}")
            print(f"   A:  {target_folder}/{filename}")
            moved += 1
        else:
            try:
                shutil.move(str(file_path), str(destination_file))
                print(f"{Colors.SUCCESS}[OK] {filename}{Colors.RESET}")
                print(f"   Movido: {file_path.relative_to(root_path)} -> {target_folder}/{filename}")
                moved += 1
            except Exception as e:
                print(f"{Colors.ERROR}Error moviendo {filename}: {e}{Colors.RESET}")
                errors += 1
    
    return moved, skipped, errors, conflicts


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Organiza archivos .sql en una carpeta centralizada"
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
    parser.add_argument(
        "--target-folder",
        type=str,
        default="scripts/sql",
        help="Carpeta destino para archivos SQL (default: scripts/sql)"
    )
    
    args = parser.parse_args()
    
    root_path = Path(args.root).resolve()
    
    if not root_path.exists():
        print(f"{Colors.ERROR}Error: La ruta {root_path} no existe{Colors.RESET}")
        sys.exit(1)
    
    moved, skipped, errors, conflicts = organize_sql_files(
        root_path, args.target_folder, args.dry_run
    )
    
    # Resumen
    print(f"\n{Colors.INFO}======================================={Colors.RESET}")
    print(f"{Colors.INFO}RESUMEN{Colors.RESET}")
    print(f"{Colors.INFO}======================================={Colors.RESET}")
    
    if args.dry_run:
        print(f"   Archivos a mover: {Colors.WARNING}{moved}{Colors.RESET}")
    else:
        print(f"   Archivos movidos: {Colors.SUCCESS}{moved}{Colors.RESET}")
    
    if conflicts > 0:
        print(f"   Archivos renombrados (conflictos): {Colors.WARNING}{conflicts}{Colors.RESET}")
    
    print(f"   Archivos omitidos: {Colors.INFO}{skipped}{Colors.RESET}")
    
    if errors > 0:
        print(f"   Errores: {Colors.ERROR}{errors}{Colors.RESET}")
    
    print(f"\n{Colors.INFO}Carpeta destino: {args.target_folder}{Colors.RESET}\n")
    print(f"{Colors.SUCCESS}[OK] Proceso completado{Colors.RESET}\n")


if __name__ == "__main__":
    main()

