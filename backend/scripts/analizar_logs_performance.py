#!/usr/bin/env python3
"""
Script para analizar logs de performance y identificar endpoints lentos

Uso:
    python scripts/analizar_logs_performance.py <archivo_log> [--threshold 1000] [--limit 20]

Ejemplo:
    python scripts/analizar_logs_performance.py logs/app.log --threshold 2000 --limit 10
"""

import argparse
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


def parse_log_line(line: str) -> Dict:
    """
    Parsear una línea de log del formato:
    YYYY-MM-DDTHH:MM:SSZ clientIP="..." requestID="..." responseTimeMS=XXX responseBytes=XXX status=XXX userAgent="..."
    """
    # Patrón para extraer métricas de performance
    pattern = r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z).*?responseTimeMS=(\d+).*?responseBytes=(\d+).*?status=(\d+).*?(GET|POST|PUT|DELETE|PATCH)\s+([^\s]+)'

    match = re.search(pattern, line)
    if not match:
        return None

    try:
        timestamp_str = match.group(1)
        response_time_ms = int(match.group(2))
        response_bytes = int(match.group(3))
        status_code = int(match.group(4))
        method = match.group(5)
        path = match.group(6).split()[0] if ' ' in match.group(6) else match.group(6)

        # Limpiar path (remover query params para agrupar mejor)
        if '?' in path:
            path = path.split('?')[0]

        return {
            "timestamp": timestamp_str,
            "method": method,
            "path": path,
            "response_time_ms": response_time_ms,
            "response_bytes": response_bytes,
            "status_code": status_code,
        }
    except (ValueError, IndexError) as e:
        return None


def analyze_logs(file_path: Path, threshold_ms: int = 1000) -> Dict:
    """Analizar logs y generar estadísticas"""
    metrics: Dict[str, Dict] = defaultdict(lambda: {
        "count": 0,
        "total_time_ms": 0,
        "min_time_ms": float('inf'),
        "max_time_ms": 0,
        "error_count": 0,
        "total_bytes": 0,
        "requests": []
    })

    total_lines = 0
    parsed_lines = 0

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                total_lines += 1
                parsed = parse_log_line(line)
                if parsed:
                    parsed_lines += 1
                    key = f"{parsed['method']}:{parsed['path']}"
                    metric = metrics[key]

                    metric["count"] += 1
                    metric["total_time_ms"] += parsed["response_time_ms"]
                    metric["min_time_ms"] = min(metric["min_time_ms"], parsed["response_time_ms"])
                    metric["max_time_ms"] = max(metric["max_time_ms"], parsed["response_time_ms"])
                    metric["total_bytes"] += parsed["response_bytes"]

                    if parsed["status_code"] >= 400:
                        metric["error_count"] += 1

                    metric["requests"].append(parsed)
    except FileNotFoundError:
        print(f"❌ Error: Archivo no encontrado: {file_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error leyendo archivo: {e}", file=sys.stderr)
        sys.exit(1)

    # Calcular promedios y generar lista de endpoints lentos
    slow_endpoints = []
    for key, metric in metrics.items():
        if metric["count"] > 0:
            avg_time_ms = metric["total_time_ms"] / metric["count"]
            avg_bytes = metric["total_bytes"] / metric["count"]
            error_rate = (metric["error_count"] / metric["count"]) * 100

            if avg_time_ms >= threshold_ms:
                method, path = key.split(':', 1)
                slow_endpoints.append({
                    "endpoint": f"{method} {path}",
                    "method": method,
                    "path": path,
                    "count": metric["count"],
                    "avg_time_ms": round(avg_time_ms, 2),
                    "min_time_ms": metric["min_time_ms"],
                    "max_time_ms": metric["max_time_ms"],
                    "error_rate": round(error_rate, 2),
                    "avg_bytes": round(avg_bytes, 2),
                })

    # Ordenar por tiempo promedio descendente
    slow_endpoints.sort(key=lambda x: x["avg_time_ms"], reverse=True)

    return {
        "total_lines": total_lines,
        "parsed_lines": parsed_lines,
        "total_endpoints": len(metrics),
        "slow_endpoints": slow_endpoints,
        "metrics": metrics,
    }


def print_report(analysis: Dict, threshold_ms: int, limit: int):
    """Imprimir reporte de análisis"""
    print("\n" + "="*80)
    print("📊 REPORTE DE ANÁLISIS DE PERFORMANCE")
    print("="*80)
    print(f"\n📈 Estadísticas Generales:")
    print(f"   - Líneas totales procesadas: {analysis['total_lines']:,}")
    print(f"   - Líneas parseadas: {analysis['parsed_lines']:,}")
    print(f"   - Endpoints únicos: {analysis['total_endpoints']}")
    print(f"   - Umbral de tiempo: {threshold_ms}ms")

    slow_endpoints = analysis['slow_endpoints'][:limit]

    if not slow_endpoints:
        print(f"\n✅ No se encontraron endpoints lentos (≥{threshold_ms}ms)")
        return

    print(f"\n🐌 Endpoints Lentos (Top {len(slow_endpoints)}):")
    print("-"*80)
    print(f"{'Endpoint':<50} {'Count':<8} {'Avg(ms)':<10} {'Max(ms)':<10} {'Errors':<8}")
    print("-"*80)

    for endpoint in slow_endpoints:
        error_indicator = "⚠️" if endpoint["error_rate"] > 0 else "  "
        print(
            f"{endpoint['endpoint']:<50} "
            f"{endpoint['count']:<8} "
            f"{endpoint['avg_time_ms']:<10.2f} "
            f"{endpoint['max_time_ms']:<10.2f} "
            f"{error_indicator} {endpoint['error_rate']:.1f}%"
        )

    print("\n" + "="*80)

    # Mostrar detalles de los 3 más lentos
    if slow_endpoints:
        print("\n🔍 Detalles de los 3 Endpoints Más Lentos:")
        print("-"*80)
        for i, endpoint in enumerate(slow_endpoints[:3], 1):
            print(f"\n{i}. {endpoint['endpoint']}")
            print(f"   - Peticiones: {endpoint['count']}")
            print(f"   - Tiempo promedio: {endpoint['avg_time_ms']}ms")
            print(f"   - Tiempo mínimo: {endpoint['min_time_ms']}ms")
            print(f"   - Tiempo máximo: {endpoint['max_time_ms']}ms")
            print(f"   - Tasa de errores: {endpoint['error_rate']}%")
            print(f"   - Tamaño promedio respuesta: {endpoint['avg_bytes']} bytes")


def main():
    parser = argparse.ArgumentParser(
        description="Analizar logs de performance y identificar endpoints lentos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python scripts/analizar_logs_performance.py logs/app.log
  python scripts/analizar_logs_performance.py logs/app.log --threshold 2000
  python scripts/analizar_logs_performance.py logs/app.log --threshold 1000 --limit 10
        """
    )
    parser.add_argument(
        "log_file",
        type=Path,
        help="Ruta al archivo de log a analizar"
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=1000,
        help="Umbral mínimo en ms para considerar un endpoint lento (default: 1000)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Número máximo de endpoints a mostrar (default: 20)"
    )

    args = parser.parse_args()

    if not args.log_file.exists():
        print(f"❌ Error: Archivo no encontrado: {args.log_file}", file=sys.stderr)
        sys.exit(1)

    print(f"🔍 Analizando logs: {args.log_file}")
    print(f"⏱️  Umbral: {args.threshold}ms")
    print(f"📊 Límite: {args.limit} endpoints")

    analysis = analyze_logs(args.log_file, threshold_ms=args.threshold)
    print_report(analysis, args.threshold, args.limit)


if __name__ == "__main__":
    main()
