#!/usr/bin/env python3
"""
Script para verificar si todos los archivos .md están ordenados en Documentos/

Este script busca archivos .md fuera de la carpeta Documentos/ y reporta
cuáles deberían moverse según las reglas de organización del proyecto.
"""

import sys
from pathlib import Path
from typing import List, Dict, Tuple

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def buscar_archivos_md_fuera_documentos() -> List[Path]:
    """Busca archivos .md fuera de la carpeta Documentos/"""
    archivos_fuera = []
    documentos_dir = project_root / "Documentos"
    
    # Buscar todos los .md en el proyecto
    for md_file in project_root.rglob("*.md"):
        # Excluir archivos dentro de Documentos/
        if documentos_dir not in md_file.parents and md_file.parent != documentos_dir:
            # Excluir también node_modules y otros directorios comunes
            if not any(excluir in str(md_file) for excluir in ['node_modules', '.git', '__pycache__', '.venv', 'venv']):
                archivos_fuera.append(md_file)
    
    return archivos_fuera

def clasificar_archivo(archivo: Path) -> str:
    """Clasifica un archivo según su nombre para sugerir dónde debería ir"""
    nombre = archivo.name.upper()
    
    # Reglas de clasificación según scripts/organizar_documentos.py
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
    elif nombre.startswith("VERIFICACION_") or nombre.startswith("CONFIRMACION_") or nombre.startswith("CHECKLIST_") or nombre.startswith("SOLUCION_") or nombre.startswith("CORRECCION_"):
        return "Documentos/General/"
    elif nombre == "README.MD":
        # Los README pueden quedarse donde están
        return "[MANTENER]"
    else:
        return "Documentos/General/"

def analizar_archivos() -> Dict:
    """Analiza los archivos .md fuera de Documentos/"""
    archivos_fuera = buscar_archivos_md_fuera_documentos()
    
    resultados = {
        'total_fuera': len(archivos_fuera),
        'por_carpeta': {},
        'por_destino': {},
        'readmes': [],
        'otros': []
    }
    
    for archivo in archivos_fuera:
        # Contar por carpeta actual
        carpeta_actual = str(archivo.parent.relative_to(project_root))
        if carpeta_actual not in resultados['por_carpeta']:
            resultados['por_carpeta'][carpeta_actual] = []
        resultados['por_carpeta'][carpeta_actual].append(archivo)
        
        # Clasificar destino sugerido
        destino = clasificar_archivo(archivo)
        if destino == "[MANTENER]":
            resultados['readmes'].append(archivo)
        else:
            if destino not in resultados['por_destino']:
                resultados['por_destino'][destino] = []
            resultados['por_destino'][destino].append(archivo)
    
    return resultados

def main():
    """Función principal"""
    print("=" * 80)
    print("VERIFICACION DE ORGANIZACION DE ARCHIVOS .MD")
    print("=" * 80)
    print()
    
    resultados = analizar_archivos()
    
    # 1. Resumen general
    print("1. RESUMEN GENERAL")
    print("-" * 80)
    print(f"Total de archivos .md fuera de Documentos/: {resultados['total_fuera']}")
    print(f"Archivos README.md (pueden mantenerse): {len(resultados['readmes'])}")
    print(f"Archivos que deberian moverse: {resultados['total_fuera'] - len(resultados['readmes'])}")
    print()
    
    # 2. Archivos por carpeta actual
    if resultados['por_carpeta']:
        print("2. ARCHIVOS POR CARPETA ACTUAL")
        print("-" * 80)
        for carpeta, archivos in sorted(resultados['por_carpeta'].items()):
            print(f"\n{carpeta}/ ({len(archivos)} archivos):")
            for archivo in sorted(archivos):
                destino = clasificar_archivo(archivo)
                if destino != "[MANTENER]":
                    print(f"  - {archivo.name}")
                    print(f"    -> Deberia moverse a: {destino}")
                else:
                    print(f"  - {archivo.name} [README - puede mantenerse]")
        print()
    
    # 3. Archivos por destino sugerido
    if resultados['por_destino']:
        print("3. ARCHIVOS POR DESTINO SUGERIDO")
        print("-" * 80)
        for destino, archivos in sorted(resultados['por_destino'].items()):
            print(f"\n{destino} ({len(archivos)} archivos):")
            for archivo in sorted(archivos):
                print(f"  - {archivo.parent.relative_to(project_root)}/{archivo.name}")
        print()
    
    # 4. READMEs que pueden mantenerse
    if resultados['readmes']:
        print("4. READMEs (PUEDEN MANTENERSE DONDE ESTAN)")
        print("-" * 80)
        for archivo in sorted(resultados['readmes']):
            print(f"  - {archivo.parent.relative_to(project_root)}/{archivo.name}")
        print()
    
    # 5. Resumen final
    print("=" * 80)
    print("RESUMEN FINAL")
    print("=" * 80)
    
    archivos_a_mover = resultados['total_fuera'] - len(resultados['readmes'])
    
    if archivos_a_mover == 0:
        print("[OK] Todos los archivos .md estan correctamente organizados!")
        print("     (Los READMEs pueden mantenerse donde estan)")
    else:
        print(f"[ADVERTENCIA] Hay {archivos_a_mover} archivos .md que deberian moverse a Documentos/")
        print()
        print("RECOMENDACIONES:")
        print("  1. Ejecutar: python scripts/organizar_documentos.py --dry-run")
        print("     para ver que archivos se moverian")
        print("  2. Ejecutar: python scripts/organizar_documentos.py")
        print("     para mover los archivos automaticamente")
        print("  3. Los READMEs pueden mantenerse donde estan")
    
    print()
    print("=" * 80)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[ADVERTENCIA] Operacion cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        import traceback
        print(f"[ERROR] Error: {e}")
        traceback.print_exc()
        sys.exit(1)
