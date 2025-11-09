#!/usr/bin/env python3
"""
Script para monitorear performance en tiempo real usando los endpoints de la API

Este script consulta los endpoints de performance y muestra métricas actualizadas.

Uso:
    python backend/scripts/monitorear_performance_tiempo_real.py [--url URL] [--intervalo SEGUNDOS]
"""

import argparse
import json
import time
from datetime import datetime
from typing import Dict, Any

import requests


def consultar_endpoint(url: str, endpoint: str) -> Dict[str, Any]:
    """Consultar un endpoint de la API"""
    try:
        full_url = f"{url}{endpoint}"
        response = requests.get(full_url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def formatear_tiempo(ms: float) -> str:
    """Formatear tiempo en ms a string legible"""
    if ms < 1000:
        return f"{ms:.0f}ms"
    elif ms < 60000:
        return f"{ms/1000:.1f}s"
    else:
        return f"{ms/60000:.1f}m"


def mostrar_resumen(summary: Dict[str, Any]):
    """Mostrar resumen de performance"""
    print("\n" + "=" * 80)
    print("📊 RESUMEN GENERAL DE PERFORMANCE")
    print("=" * 80)

    if "error" in summary:
        print(f"❌ Error: {summary['error']}")
        return

    data = summary.get("summary", {})
    print(f"Total de endpoints: {data.get('total_endpoints', 0)}")
    print(f"Total de peticiones: {data.get('total_requests', 0):,}")
    print(f"Tiempo promedio: {formatear_tiempo(data.get('avg_response_time_ms', 0))}")
    print(f"Tasa de errores: {data.get('error_rate', 0):.2f}%")
    print(f"Total de errores: {data.get('total_errors', 0)}")
    if "monitoring_since" in data:
        print(f"Monitoreando desde: {data['monitoring_since']}")


def mostrar_endpoints_lentos(slow_endpoints: Dict[str, Any], threshold_ms: float = 1000):
    """Mostrar lista de endpoints lentos"""
    print("\n" + "=" * 80)
    print(f"🐌 ENDPOINTS LENTOS (> {formatear_tiempo(threshold_ms)})")
    print("=" * 80)

    if "error" in slow_endpoints:
        print(f"❌ Error: {slow_endpoints['error']}")
        return

    endpoints = slow_endpoints.get("endpoints", [])
    if not endpoints:
        print("✅ No hay endpoints lentos actualmente")
        return

    print(f"Encontrados {len(endpoints)} endpoints lentos:\n")
    print(f"{'Endpoint':<50} {'Tiempo Prom':<15} {'Min':<10} {'Max':<10} {'Count':<8}")
    print("-" * 80)

    for ep in endpoints[:10]:  # Mostrar solo los primeros 10
        metodo_path = ep.get("method_path", "N/A")
        tiempo_prom = ep.get("avg_time_ms", 0)
        tiempo_min = ep.get("min_time_ms", 0)
        tiempo_max = ep.get("max_time_ms", 0)
        count = ep.get("count", 0)

        # Truncar si es muy largo
        if len(metodo_path) > 48:
            metodo_path = metodo_path[:45] + "..."

        print(
            f"{metodo_path:<50} {formatear_tiempo(tiempo_prom):<15} "
            f"{formatear_tiempo(tiempo_min):<10} {formatear_tiempo(tiempo_max):<10} {count:<8}"
        )


def mostrar_peticiones_recientes(recent: Dict[str, Any], limit: int = 5):
    """Mostrar peticiones recientes"""
    print("\n" + "=" * 80)
    print(f"🕐 ÚLTIMAS {limit} PETICIONES")
    print("=" * 80)

    if "error" in recent:
        print(f"❌ Error: {recent['error']}")
        return

    requests_list = recent.get("requests", [])
    if not requests_list:
        print("No hay peticiones recientes")
        return

    print(f"{'Timestamp':<25} {'Método + Path':<40} {'Tiempo':<12} {'Status':<8}")
    print("-" * 80)

    for req in requests_list[-limit:]:
        timestamp = datetime.fromtimestamp(req.get("timestamp", 0)).strftime("%Y-%m-%d %H:%M:%S")
        metodo = req.get("method", "N/A")
        path = req.get("path", "N/A")
        metodo_path = f"{metodo} {path}"
        if len(metodo_path) > 38:
            metodo_path = metodo_path[:35] + "..."
        tiempo = formatear_tiempo(req.get("response_time_ms", 0))
        status = req.get("status_code", "N/A")

        # Colorear según tiempo
        emoji = "🐌" if req.get("response_time_ms", 0) > 5000 else "⚠️" if req.get("response_time_ms", 0) > 2000 else "✅"

        print(f"{emoji} {timestamp:<23} {metodo_path:<40} {tiempo:<12} {status:<8}")


def main():
    parser = argparse.ArgumentParser(description="Monitorear performance en tiempo real")
    parser.add_argument(
        "--url",
        default="https://pagos-f2qf.onrender.com/api/v1",
        help="URL base de la API (default: https://pagos-f2qf.onrender.com/api/v1)",
    )
    parser.add_argument(
        "--intervalo",
        type=int,
        default=30,
        help="Intervalo en segundos entre actualizaciones (default: 30)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=1000,
        help="Umbral en ms para considerar endpoint lento (default: 1000)",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("🔍 MONITOR DE PERFORMANCE EN TIEMPO REAL")
    print("=" * 80)
    print(f"URL: {args.url}")
    print(f"Intervalo: {args.intervalo} segundos")
    print(f"Umbral de endpoints lentos: {formatear_tiempo(args.threshold)}")
    print("Presiona Ctrl+C para salir")
    print()

    try:
        while True:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n🔄 Actualizando métricas... ({timestamp})")

            # Consultar endpoints
            summary = consultar_endpoint(args.url, "/performance/summary")
            slow_endpoints = consultar_endpoint(args.url, f"/performance/slow?threshold_ms={args.threshold}")
            recent = consultar_endpoint(args.url, "/performance/recent?limit=5")

            # Mostrar resultados
            mostrar_resumen(summary)
            mostrar_endpoints_lentos(slow_endpoints, args.threshold)
            mostrar_peticiones_recientes(recent, limit=5)

            print("\n" + "=" * 80)
            print(f"⏳ Esperando {args.intervalo} segundos antes de la próxima actualización...")
            print("=" * 80)

            time.sleep(args.intervalo)

    except KeyboardInterrupt:
        print("\n\n👋 Monitoreo detenido por el usuario")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
