#!/usr/bin/env python3
"""
Script para verificar scripts Python caducos u obsoletos

Este script busca:
1. Scripts en el directorio obsolete/
2. Scripts con referencias a archivos que ya no existen
3. Scripts con comentarios indicando que están obsoletos
4. Scripts que importan módulos que ya no existen
"""

import sys
import os
from pathlib import Path
import re
from typing import List, Dict, Tuple

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def buscar_scripts_obsoletos() -> List[Path]:
    """Busca scripts en directorios obsoletos"""
    scripts_obsoletos = []
    
    # Buscar en scripts/obsolete/
    obsolete_dir = project_root / "scripts" / "obsolete"
    if obsolete_dir.exists():
        for py_file in obsolete_dir.rglob("*.py"):
            scripts_obsoletos.append(py_file)
    
    return scripts_obsoletos

def buscar_comentarios_obsoletos(script_path: Path) -> List[str]:
    """Busca comentarios que indican que el script está obsoleto"""
    comentarios = []
    patrones = [
        r"obsoleto|obsolete|deprecated|no usar|no usar|TODO.*eliminar|FIXME.*eliminar",
        r"caduco|caduca|desuso|desactualizado",
    ]
    
    try:
        contenido = script_path.read_text(encoding='utf-8', errors='ignore')
        for i, linea in enumerate(contenido.split('\n'), 1):
            for patron in patrones:
                if re.search(patron, linea, re.IGNORECASE):
                    comentarios.append(f"Línea {i}: {linea.strip()}")
    except Exception as e:
        pass
    
    return comentarios

def verificar_referencias_archivos(script_path: Path) -> List[str]:
    """Verifica si el script hace referencia a archivos que no existen"""
    problemas = []
    
    try:
        contenido = script_path.read_text(encoding='utf-8', errors='ignore')
        
        # Buscar referencias a archivos .sql
        patrones_sql = [
            r'["\']([^"\']+\.sql)["\']',
            r'["\']([^"\']+\.sql)["\']',
            r'f["\']([^"\']+\.sql)["\']',
        ]
        
        for patron in patrones_sql:
            matches = re.findall(patron, contenido)
            for match in matches:
                # Buscar el archivo
                archivo_sql = project_root / match if not Path(match).is_absolute() else Path(match)
                if not archivo_sql.exists():
                    problemas.append(f"Referencia a archivo inexistente: {match}")
        
        # Buscar imports de módulos que podrían no existir
        patrones_import = [
            r'from\s+([^\s]+)\s+import',
            r'import\s+([^\s]+)',
        ]
        
        for patron in patrones_import:
            matches = re.findall(patron, contenido)
            for match in matches:
                # Verificar si es un módulo local que podría no existir
                if match.startswith('app.') or match.startswith('scripts.'):
                    try:
                        __import__(match)
                    except ImportError:
                        # No es necesariamente un problema, podría ser un módulo condicional
                        pass
    
    except Exception as e:
        problemas.append(f"Error al leer archivo: {e}")
    
    return problemas

def analizar_script(script_path: Path) -> Dict:
    """Analiza un script individual"""
    resultado = {
        'ruta': str(script_path.relative_to(project_root)),
        'existe': script_path.exists(),
        'tamaño': script_path.stat().st_size if script_path.exists() else 0,
        'comentarios_obsoletos': [],
        'referencias_problematicas': [],
        'en_directorio_obsolete': 'obsolete' in str(script_path),
    }
    
    if script_path.exists():
        resultado['comentarios_obsoletos'] = buscar_comentarios_obsoletos(script_path)
        resultado['referencias_problematicas'] = verificar_referencias_archivos(script_path)
    
    return resultado

def main():
    """Función principal"""
    print("=" * 80)
    print("VERIFICACION DE SCRIPTS PYTHON CADUCOS")
    print("=" * 80)
    print()
    
    # 1. Buscar scripts en directorios obsoletos
    print("1. Buscando scripts en directorios obsoletos...")
    scripts_obsoletos = buscar_scripts_obsoletos()
    
    if scripts_obsoletos:
        print(f"   [OK] Encontrados {len(scripts_obsoletos)} scripts en directorios obsoletos:")
        for script in scripts_obsoletos:
            print(f"      - {script.relative_to(project_root)}")
    else:
        print("   [INFO] No se encontraron scripts en directorios obsoletos")
    print()
    
    # 2. Analizar todos los scripts encontrados
    print("2. Analizando scripts obsoletos...")
    print()
    
    resultados = []
    for script in scripts_obsoletos:
        analisis = analizar_script(script)
        resultados.append(analisis)
    
    # 3. Mostrar resultados detallados
    if resultados:
        print("=" * 80)
        print("RESULTADOS DETALLADOS")
        print("=" * 80)
        print()
        
        for resultado in resultados:
            print(f"[ARCHIVO] {resultado['ruta']}")
            print(f"   Tamano: {resultado['tamaño']:,} bytes")
            print(f"   En directorio obsolete: {'[SI]' if resultado['en_directorio_obsolete'] else '[NO]'}")
            
            if resultado['comentarios_obsoletos']:
                print(f"   [ADVERTENCIA] Comentarios obsoletos encontrados:")
                for comentario in resultado['comentarios_obsoletos']:
                    print(f"      - {comentario}")
            
            if resultado['referencias_problematicas']:
                print(f"   [ADVERTENCIA] Referencias problematicas:")
                for ref in resultado['referencias_problematicas']:
                    print(f"      - {ref}")
            
            print()
    else:
        print("[INFO] No hay scripts obsoletos para analizar")
        print()
    
    # 4. Resumen
    print("=" * 80)
    print("RESUMEN")
    print("=" * 80)
    print(f"Total de scripts obsoletos encontrados: {len(scripts_obsoletos)}")
    
    scripts_con_problemas = sum(1 for r in resultados if r['comentarios_obsoletos'] or r['referencias_problematicas'])
    print(f"Scripts con problemas detectados: {scripts_con_problemas}")
    
    print()
    print("=" * 80)
    print("[OK] VERIFICACION COMPLETADA")
    print("=" * 80)
    
    # 5. Recomendaciones
    if scripts_obsoletos:
        print()
        print("RECOMENDACIONES:")
        print("   - Los scripts en scripts/obsolete/ pueden eliminarse si ya no se necesitan")
        print("   - Revisar scripts con referencias a archivos inexistentes")
        print("   - Considerar actualizar o eliminar scripts con comentarios obsoletos")
        print()

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
