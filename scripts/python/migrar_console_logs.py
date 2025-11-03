"""
Script para migrar console.log a logger estructurado en frontend
Identifica y sugiere migración de console.log a logger
"""

import re
import os
from pathlib import Path
from typing import List, Dict, Tuple

def find_console_logs(directory: str = "frontend/src") -> Dict[str, List[Tuple[int, str]]]:
    """
    Encuentra todos los console.log en el directorio
    Retorna: {archivo: [(línea, contenido), ...]}
    """
    results = {}
    frontend_path = Path(directory)
    
    patterns = [
        r'console\.log\s*\(',
        r'console\.error\s*\(',
        r'console\.warn\s*\(',
        r'console\.debug\s*\(',
        r'console\.info\s*\(',
    ]
    
    for file_path in frontend_path.rglob("*.tsx"):
        if "node_modules" in str(file_path):
            continue
            
        matches = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    for pattern in patterns:
                        if re.search(pattern, line):
                            matches.append((line_num, line.strip()))
                            break
        except Exception as e:
            print(f"Error leyendo {file_path}: {e}")
            continue
            
        if matches:
            results[str(file_path)] = matches
    
    for file_path in frontend_path.rglob("*.ts"):
        if "node_modules" in str(file_path) or file_path.name in ["logger.ts", "safeConsole.ts"]:
            continue
            
        matches = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    for pattern in patterns:
                        if re.search(pattern, line):
                            matches.append((line_num, line.strip()))
                            break
        except Exception as e:
            print(f"Error leyendo {file_path}: {e}")
            continue
            
        if matches:
            results[str(file_path)] = matches
    
    return results


def generate_migration_report(results: Dict[str, List[Tuple[int, str]]]):
    """Genera reporte de migración"""
    print("\n" + "="*80)
    print("REPORTE DE MIGRACIÓN: console.log → logger")
    print("="*80)
    print(f"\nTotal archivos con console.*: {len(results)}")
    
    total_logs = sum(len(matches) for matches in results.values())
    print(f"Total instancias: {total_logs}\n")
    
    # Agrupar por tipo
    by_type = {
        "log": 0,
        "error": 0,
        "warn": 0,
        "debug": 0,
        "info": 0
    }
    
    for matches in results.values():
        for _, line in matches:
            if "console.log" in line:
                by_type["log"] += 1
            elif "console.error" in line:
                by_type["error"] += 1
            elif "console.warn" in line:
                by_type["warn"] += 1
            elif "console.debug" in line:
                by_type["debug"] += 1
            elif "console.info" in line:
                by_type["info"] += 1
    
    print("Distribución por tipo:")
    for log_type, count in by_type.items():
        if count > 0:
            print(f"  console.{log_type}: {count}")
    
    print("\n" + "-"*80)
    print("ARCHIVOS CON MÁS INSTANCIAS (Top 10):")
    print("-"*80)
    
    sorted_files = sorted(results.items(), key=lambda x: len(x[1]), reverse=True)
    for file_path, matches in sorted_files[:10]:
        rel_path = Path(file_path).relative_to("frontend/src")
        print(f"  {rel_path}: {len(matches)} instancias")
    
    print("\n" + "="*80)
    print("RECOMENDACIONES:")
    print("="*80)
    print("1. Migrar archivos críticos primero (components, pages)")
    print("2. Usar logger.info() para console.log")
    print("3. Usar logger.error() para console.error")
    print("4. Remover console.log de producción automáticamente")
    print("\nEjemplo de migración:")
    print("  Antes: console.log('Debug:', data)")
    print("  Después: logger.info('Debug', { data })")
    print("="*80 + "\n")


if __name__ == "__main__":
    results = find_console_logs()
    generate_migration_report(results)
    
    # Guardar resultados en archivo
    report_path = Path("Documentos/Auditorias/REPORTE_CONSOLE_LOGS.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# 📋 REPORTE DE CONSOLE.LOG EN FRONTEND\n\n")
        f.write(f"**Total archivos:** {len(results)}\n")
        f.write(f"**Total instancias:** {sum(len(matches) for matches in results.values())}\n\n")
        f.write("## Archivos con console.log\n\n")
        
        for file_path, matches in sorted(results.items(), key=lambda x: len(x[1]), reverse=True):
            rel_path = Path(file_path).relative_to("frontend/src")
            f.write(f"### {rel_path} ({len(matches)} instancias)\n\n")
            for line_num, line in matches[:5]:  # Mostrar solo primeras 5
                f.write(f"- Línea {line_num}: `{line}`\n")
            if len(matches) > 5:
                f.write(f"- ... y {len(matches) - 5} más\n")
            f.write("\n")
    
    print(f"\n✅ Reporte guardado en: {report_path}")

