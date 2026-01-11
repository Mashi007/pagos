#!/usr/bin/env python3
"""
Script para mover archivos .md a Documentos/ según su clasificación
"""

import sys
import shutil
from pathlib import Path
from typing import List, Tuple

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def clasificar_archivo(archivo: Path) -> str:
    """Clasifica un archivo según su nombre"""
    nombre = archivo.name.upper()
    
    if nombre.startswith("AUDITORIA_"):
        return "Documentos/Auditorias/"
    elif nombre.startswith("ANALISIS_"):
        return "Documentos/Analisis/"
    elif nombre.startswith("TEST_") or "CI-CD" in nombre or "ACCESIBILIDAD" in nombre:
        return "Documentos/Testing/"
    elif nombre.startswith("INSTALAR_") or "COMANDOS_INSTALACION" in nombre or "PASOS_INSTALACION" in nombre or "DEPLOYMENT" in nombre or "VERIFICAR_INSTALACION" in nombre:
        return "Documentos/Configuracion/"
    elif nombre.startswith("PROCEDIMIENTO_") or nombre.startswith("AVANCE_") or nombre.startswith("ESTADO_FINAL_") or "ESTADO_CLIENTES" in nombre or nombre.startswith("RESUMEN_CAMBIOS_") or nombre.startswith("RESUMEN_ERRORES_") or nombre.startswith("PROPUESTA_"):
        return "Documentos/Desarrollo/"
    elif nombre == "README.MD":
        return None  # No mover READMEs
    else:
        return "Documentos/General/"

def buscar_archivos_md_fuera_documentos() -> List[Path]:
    """Busca archivos .md fuera de Documentos/"""
    archivos_fuera = []
    documentos_dir = project_root / "Documentos"
    
    for md_file in project_root.rglob("*.md"):
        if documentos_dir not in md_file.parents and md_file.parent != documentos_dir:
            if not any(excluir in str(md_file) for excluir in ['node_modules', '.git', '__pycache__', '.venv', 'venv', '.pytest_cache']):
                archivos_fuera.append(md_file)
    
    return archivos_fuera

def mover_archivos(dry_run: bool = False) -> Tuple[int, int, int]:
    """Mueve archivos .md a sus carpetas correspondientes"""
    archivos = buscar_archivos_md_fuera_documentos()
    movidos = 0
    omitidos = 0
    errores = 0
    
    print("=" * 80)
    print("ORGANIZACION DE ARCHIVOS .MD")
    print("=" * 80)
    print()
    
    if dry_run:
        print("[MODO DRY-RUN] No se moveran archivos, solo se mostrara lo que se haria")
        print()
    
    for archivo in archivos:
        destino_carpeta = clasificar_archivo(archivo)
        
        if destino_carpeta is None:
            # README - omitir
            omitidos += 1
            continue
        
        destino_path = project_root / destino_carpeta
        destino_completo = destino_path / archivo.name
        
        # Crear carpeta destino si no existe
        if not dry_run:
            destino_path.mkdir(parents=True, exist_ok=True)
        
        # Verificar si ya existe
        if destino_completo.exists():
            print(f"[OMITIDO] Ya existe: {destino_completo.relative_to(project_root)}")
            omitidos += 1
            continue
        
        try:
            if dry_run:
                print(f"[MOVERA] {archivo.relative_to(project_root)} -> {destino_completo.relative_to(project_root)}")
            else:
                shutil.move(str(archivo), str(destino_completo))
                print(f"[MOVIDO] {archivo.relative_to(project_root)} -> {destino_completo.relative_to(project_root)}")
            movidos += 1
        except Exception as e:
            print(f"[ERROR] No se pudo mover {archivo.relative_to(project_root)}: {e}")
            errores += 1
    
    print()
    print("=" * 80)
    print("RESUMEN")
    print("=" * 80)
    print(f"Archivos movidos: {movidos}")
    print(f"Archivos omitidos: {omitidos}")
    print(f"Errores: {errores}")
    print("=" * 80)
    
    return movidos, omitidos, errores

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Organizar archivos .md en Documentos/')
    parser.add_argument('--dry-run', action='store_true', help='Solo mostrar que se moveria sin mover archivos')
    args = parser.parse_args()
    
    try:
        mover_archivos(dry_run=args.dry_run)
    except KeyboardInterrupt:
        print("\n[ADVERTENCIA] Operacion cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        import traceback
        print(f"[ERROR] Error: {e}")
        traceback.print_exc()
        sys.exit(1)
