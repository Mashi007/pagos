"""
Script para analizar y priorizar funciones con complejidad ciclomática alta
Genera reporte detallado con recomendaciones de refactorización
"""
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict


def ejecutar_flake8_complexity() -> List[str]:
    """Ejecuta flake8 con análisis de complejidad y retorna líneas de salida"""
    try:
        backend_dir = Path(__file__).parent.parent / "backend"
        if not backend_dir.exists():
            print(f"[ERROR] Directorio backend no encontrado: {backend_dir}")
            return []
        
        result = subprocess.run(
            ["python", "-m", "flake8", "app/", "--select=C901", "--format=%(path)s:%(row)d: %(text)s"],
            cwd=str(backend_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        output = result.stdout.strip() if result.stdout.strip() else ""
        if output:
            return output.split("\n")
        return []
    except Exception as e:
        print(f"[ERROR] Error ejecutando flake8: {e}")
        return []


def parsear_complejidad(linea: str) -> Tuple[str, int, int, int]:
    """
    Parsea línea de flake8 para extraer:
    (archivo, línea, complejidad, nombre_función)
    """
    # Formato: app/path/file.py:123: C901 'function_name' is too complex (15)
    match = re.search(r"app/(.+?):(\d+):.*?complex \((\d+)\)", linea)
    if match:
        archivo = match.group(1)
        linea_num = int(match.group(2))
        complejidad = int(match.group(3))
        
        # Intentar extraer nombre de función
        func_match = re.search(r"'([^']+)'", linea)
        nombre_func = func_match.group(1) if func_match else "unknown"
        
        return (archivo, linea_num, complejidad, nombre_func)
    return None


def categorizar_complejidad(complejidad: int) -> str:
    """Categoriza el nivel de complejidad"""
    if complejidad >= 40:
        return "CRITICA"
    elif complejidad >= 20:
        return "ALTA"
    elif complejidad >= 15:
        return "MEDIA"
    else:
        return "BAJA"


def analizar_funciones() -> Dict[str, List[Dict]]:
    """Analiza todas las funciones con complejidad alta"""
    lineas = ejecutar_flake8_complexity()
    
    funciones_por_categoria = defaultdict(list)
    funciones_por_archivo = defaultdict(list)
    
    for linea in lineas:
        if not linea.strip():
            continue
        
        parsed = parsear_complejidad(linea)
        if not parsed:
            continue
        
        archivo, linea_num, complejidad, nombre_func = parsed
        categoria = categorizar_complejidad(complejidad)
        
        info_funcion = {
            "archivo": archivo,
            "linea": linea_num,
            "complejidad": complejidad,
            "nombre": nombre_func,
            "categoria": categoria
        }
        
        funciones_por_categoria[categoria].append(info_funcion)
        funciones_por_archivo[archivo].append(info_funcion)
    
    # Ordenar por complejidad descendente
    for categoria in funciones_por_categoria:
        funciones_por_categoria[categoria].sort(key=lambda x: x["complejidad"], reverse=True)
    
    for archivo in funciones_por_archivo:
        funciones_por_archivo[archivo].sort(key=lambda x: x["complejidad"], reverse=True)
    
    return {
        "por_categoria": dict(funciones_por_categoria),
        "por_archivo": dict(funciones_por_archivo),
        "total": len([f for cat in funciones_por_categoria.values() for f in cat])
    }


def generar_reporte_texto(analisis: Dict) -> str:
    """Genera reporte en formato texto"""
    reporte = []
    reporte.append("=" * 80)
    reporte.append("REPORTE DE COMPLEJIDAD CICLOMÁTICA")
    reporte.append("=" * 80)
    reporte.append(f"\nTotal de funciones con complejidad > 10: {analisis['total']}")
    reporte.append("")
    
    # Por categoría
    reporte.append("DISTRIBUCION POR CATEGORIA:")
    reporte.append("-" * 80)
    for categoria in ["CRITICA", "ALTA", "MEDIA", "BAJA"]:
        funciones = analisis["por_categoria"].get(categoria, [])
        if funciones:
            reporte.append(f"\n{categoria}: {len(funciones)} funciones")
            for func in funciones[:10]:  # Top 10 por categoría
                reporte.append(
                    f"  • {func['archivo']}:{func['linea']} - {func['nombre']} "
                    f"(complejidad: {func['complejidad']})"
                )
            if len(funciones) > 10:
                reporte.append(f"  ... y {len(funciones) - 10} más")
    
    # Por archivo
    reporte.append("\n\nFUNCIONES POR ARCHIVO:")
    reporte.append("-" * 80)
    for archivo, funciones in sorted(analisis["por_archivo"].items(), 
                                      key=lambda x: len(x[1]), reverse=True)[:15]:
        reporte.append(f"\n{archivo}: {len(funciones)} funciones")
        for func in funciones[:5]:  # Top 5 por archivo
            reporte.append(
                f"  • Línea {func['linea']}: {func['nombre']} "
                f"(complejidad: {func['complejidad']}, {func['categoria']})"
            )
        if len(funciones) > 5:
            reporte.append(f"  ... y {len(funciones) - 5} más")
    
    # Top 20 funciones más complejas
    reporte.append("\n\nTOP 20 FUNCIONES MAS COMPLEJAS:")
    reporte.append("-" * 80)
    todas_funciones = [
        f for cat in analisis["por_categoria"].values() for f in cat
    ]
    todas_funciones.sort(key=lambda x: x["complejidad"], reverse=True)
    
    for i, func in enumerate(todas_funciones[:20], 1):
        reporte.append(
            f"{i:2d}. {func['archivo']}:{func['linea']} - {func['nombre']} "
            f"(complejidad: {func['complejidad']}, {func['categoria']})"
        )
    
    return "\n".join(reporte)


def generar_reporte_markdown(analisis: Dict, output_file: Path):
    """Genera reporte en formato Markdown"""
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# Reporte de Complejidad Ciclomatica\n\n")
        f.write(f"**Total de funciones con complejidad > 10:** {analisis['total']}\n\n")
        
        # Resumen por categoría
        f.write("## Resumen por Categoria\n\n")
        f.write("| Categoría | Cantidad | Prioridad |\n")
        f.write("|-----------|----------|-----------|\n")
        f.write("| CRITICA (>=40) | {} | URGENTE |\n".format(
            len(analisis["por_categoria"].get("CRITICA", []))
        ))
        f.write("| ALTA (20-39) | {} | Alta |\n".format(
            len(analisis["por_categoria"].get("ALTA", []))
        ))
        f.write("| MEDIA (15-19) | {} | Media |\n".format(
            len(analisis["por_categoria"].get("MEDIA", []))
        ))
        f.write("| BAJA (11-14) | {} | Baja |\n\n".format(
            len(analisis["por_categoria"].get("BAJA", []))
        ))
        
        # Top funciones críticas
        f.write("## Funciones Criticas (Complejidad >= 40)\n\n")
        funciones_criticas = analisis["por_categoria"].get("CRITICA", [])
        if funciones_criticas:
            f.write("| # | Archivo | Línea | Función | Complejidad |\n")
            f.write("|---|---------|-------|---------|-------------|\n")
            for i, func in enumerate(funciones_criticas, 1):
                f.write(
                    f"| {i} | `{func['archivo']}` | {func['linea']} | "
                    f"`{func['nombre']}` | **{func['complejidad']}** |\n"
                )
        else:
            f.write("[OK] No hay funciones criticas.\n")
        
        f.write("\n## 📁 Distribución por Archivo\n\n")
        for archivo, funciones in sorted(analisis["por_archivo"].items(),
                                         key=lambda x: len(x[1]), reverse=True)[:20]:
            f.write(f"### `{archivo}` ({len(funciones)} funciones)\n\n")
            for func in funciones[:10]:
                f.write(
                    f"- **Línea {func['linea']}:** `{func['nombre']}` "
                    f"- Complejidad: {func['complejidad']} ({func['categoria']})\n"
                )
            if len(funciones) > 10:
                f.write(f"- ... y {len(funciones) - 10} más\n")
            f.write("\n")


def main():
    """Función principal"""
    print("[INFO] Analizando complejidad ciclomatica...")
    
    analisis = analizar_funciones()
    
    if analisis["total"] == 0:
        print("[OK] No se encontraron funciones con complejidad > 10")
        return
    
    # Generar reporte texto
    reporte_texto = generar_reporte_texto(analisis)
    print("\n" + reporte_texto)
    
    # Guardar reporte en archivo
    backend_dir = Path(__file__).parent.parent / "backend"
    reporte_file = backend_dir.parent / "Documentos" / "Analisis" / "REPORTE_COMPLEJIDAD_CICLOMATICA.md"
    reporte_file.parent.mkdir(parents=True, exist_ok=True)
    
    generar_reporte_markdown(analisis, reporte_file)
    print(f"\n[OK] Reporte guardado en: {reporte_file}")
    
    # Estadísticas
    print("\n[ESTADISTICAS]")
    print(f"  Total de funciones: {analisis['total']}")
    for categoria in ["CRITICA", "ALTA", "MEDIA", "BAJA"]:
        count = len(analisis["por_categoria"].get(categoria, []))
        if count > 0:
            porcentaje = (count / analisis["total"]) * 100
            print(f"  {categoria}: {count} ({porcentaje:.1f}%)")


if __name__ == "__main__":
    main()

