#!/usr/bin/env python3
"""
Script para analizar logs y detectar patrones anómalos de seguridad
Detecta:
- Solicitudes repetitivas desde la misma IP
- Intervalos regulares sospechosos
- Posibles bots o scrapers
- Patrones de ataque

Uso:
    python scripts/analizar_logs_seguridad.py <archivo_log> [--window 60] [--threshold 10]

Ejemplo:
    python scripts/analizar_logs_seguridad.py logs/app.log --window 60 --threshold 10
"""

import argparse
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple


def parse_log_line(line: str) -> Dict:
    """
    Parsear una línea de log del formato:
    YYYY-MM-DDTHH:MM:SSZ clientIP="..." requestID="..." responseTimeMS=XXX responseBytes=XXX userAgent="..."
    """
    # Patrón para extraer información de seguridad
    pattern = r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z).*?clientIP="([^"]+)".*?requestID="([^"]+)".*?responseTimeMS=(\d+).*?responseBytes=(\d+).*?userAgent="([^"]+)".*?(GET|POST|PUT|DELETE|PATCH)\s+([^\s]+)'

    match = re.search(pattern, line)
    if not match:
        return None

    try:
        timestamp_str = match.group(1)
        client_ip = match.group(2)
        request_id = match.group(3)
        response_time_ms = int(match.group(4))
        response_bytes = int(match.group(5))
        user_agent = match.group(6)
        method = match.group(7)
        path = match.group(8).split()[0] if ' ' in match.group(8) else match.group(8)

        # Limpiar path (remover query params para agrupar mejor)
        if '?' in path:
            path = path.split('?')[0]

        # Parsear timestamp
        try:
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            timestamp = None

        return {
            "timestamp": timestamp,
            "timestamp_str": timestamp_str,
            "client_ip": client_ip,
            "request_id": request_id,
            "response_time_ms": response_time_ms,
            "response_bytes": response_bytes,
            "user_agent": user_agent,
            "method": method,
            "path": path,
        }
    except (ValueError, IndexError) as e:
        return None


def analyze_suspicious_patterns(logs: List[Dict], window_seconds: int = 60, threshold: int = 10) -> Dict:
    """
    Analizar patrones sospechosos en los logs
    """
    # Agrupar por IP
    ip_requests: Dict[str, List[Dict]] = defaultdict(list)
    for log in logs:
        if log and log.get("client_ip"):
            ip_requests[log["client_ip"]].append(log)

    suspicious_ips = []

    for ip, requests in ip_requests.items():
        if len(requests) < threshold:
            continue

        # Ordenar por timestamp
        requests_sorted = sorted([r for r in requests if r.get("timestamp")], key=lambda x: x["timestamp"])

        if len(requests_sorted) < 2:
            continue

        # Analizar intervalos entre solicitudes
        intervals = []
        for i in range(1, len(requests_sorted)):
            if requests_sorted[i]["timestamp"] and requests_sorted[i-1]["timestamp"]:
                delta = (requests_sorted[i]["timestamp"] - requests_sorted[i-1]["timestamp"]).total_seconds()
                intervals.append(delta)

        if not intervals:
            continue

        # Calcular estadísticas de intervalos
        avg_interval = sum(intervals) / len(intervals) if intervals else 0
        min_interval = min(intervals) if intervals else 0
        max_interval = max(intervals) if intervals else 0

        # Detectar intervalos regulares (desviación estándar baja)
        if len(intervals) > 1:
            variance = sum((x - avg_interval) ** 2 for x in intervals) / len(intervals)
            std_dev = variance ** 0.5
        else:
            std_dev = 0

        # Calcular solicitudes por ventana de tiempo
        if requests_sorted:
            first_time = requests_sorted[0]["timestamp"]
            last_time = requests_sorted[-1]["timestamp"]
            time_span = (last_time - first_time).total_seconds()
            requests_per_window = len(requests_sorted) / (time_span / window_seconds) if time_span > 0 else len(requests_sorted)
        else:
            requests_per_window = 0

        # Detectar patrones sospechosos
        is_suspicious = False
        suspicious_reasons = []

        # 1. Muchas solicitudes en ventana de tiempo
        if requests_per_window >= threshold:
            is_suspicious = True
            suspicious_reasons.append(f"Alta frecuencia: {requests_per_window:.1f} solicitudes/{window_seconds}s")

        # 2. Intervalos muy regulares (posible bot)
        if std_dev < 2 and avg_interval > 0 and avg_interval < 30:
            is_suspicious = True
            suspicious_reasons.append(f"Intervalos regulares: {avg_interval:.1f}s ± {std_dev:.2f}s")

        # 3. Intervalos muy cortos
        if min_interval < 1 and len(requests_sorted) > 5:
            is_suspicious = True
            suspicious_reasons.append(f"Intervalos muy cortos: mínimo {min_interval:.2f}s")

        # 4. Mismo user agent en todas las solicitudes
        user_agents = set(r.get("user_agent", "") for r in requests_sorted)
        if len(user_agents) == 1 and len(requests_sorted) > 10:
            is_suspicious = True
            suspicious_reasons.append(f"Mismo user agent: {list(user_agents)[0]}")

        # 5. Mismo path repetido
        paths = [r.get("path", "") for r in requests_sorted]
        unique_paths = len(set(paths))
        if unique_paths == 1 and len(requests_sorted) > 5:
            is_suspicious = True
            suspicious_reasons.append(f"Mismo endpoint repetido: {paths[0]}")

        if is_suspicious:
            suspicious_ips.append({
                "ip": ip,
                "total_requests": len(requests_sorted),
                "time_span_seconds": time_span,
                "requests_per_window": requests_per_window,
                "avg_interval": avg_interval,
                "min_interval": min_interval,
                "max_interval": max_interval,
                "std_dev_interval": std_dev,
                "user_agents": list(user_agents),
                "unique_paths": unique_paths,
                "paths": list(set(paths)),
                "first_request": requests_sorted[0]["timestamp_str"] if requests_sorted else None,
                "last_request": requests_sorted[-1]["timestamp_str"] if requests_sorted else None,
                "suspicious_reasons": suspicious_reasons,
            })

    # Ordenar por número de solicitudes
    suspicious_ips.sort(key=lambda x: x["total_requests"], reverse=True)

    return {
        "total_ips": len(ip_requests),
        "suspicious_ips": suspicious_ips,
        "window_seconds": window_seconds,
        "threshold": threshold,
    }


def print_report(analysis: Dict):
    """Imprimir reporte de análisis de seguridad"""
    print("\n" + "="*80)
    print("🔒 REPORTE DE ANÁLISIS DE SEGURIDAD")
    print("="*80)
    print(f"\n📊 Estadísticas Generales:")
    print(f"   - IPs únicas analizadas: {analysis['total_ips']}")
    print(f"   - Ventana de análisis: {analysis['window_seconds']} segundos")
    print(f"   - Umbral de detección: {analysis['threshold']} solicitudes")

    suspicious_ips = analysis['suspicious_ips']

    if not suspicious_ips:
        print(f"\n✅ No se encontraron patrones sospechosos")
        return

    print(f"\n⚠️  IPs Sospechosas Detectadas: {len(suspicious_ips)}")
    print("-"*80)

    for i, ip_data in enumerate(suspicious_ips, 1):
        print(f"\n{i}. 🚨 IP: {ip_data['ip']}")
        print(f"   📈 Total de solicitudes: {ip_data['total_requests']}")
        print(f"   ⏱️  Período: {ip_data['first_request']} → {ip_data['last_request']}")
        print(f"   📊 Frecuencia: {ip_data['requests_per_window']:.1f} solicitudes/{analysis['window_seconds']}s")
        print(f"   ⏳ Intervalo promedio: {ip_data['avg_interval']:.2f}s")
        print(f"   📉 Intervalo mínimo: {ip_data['min_interval']:.2f}s")
        print(f"   📈 Intervalo máximo: {ip_data['max_interval']:.2f}s")
        print(f"   📐 Desviación estándar: {ip_data['std_dev_interval']:.2f}s")
        print(f"   🌐 User Agents: {len(ip_data['user_agents'])} único(s)")
        for ua in ip_data['user_agents'][:2]:  # Mostrar máximo 2
            print(f"      - {ua[:80]}...")
        print(f"   🔗 Endpoints únicos: {ip_data['unique_paths']}")
        if ip_data['unique_paths'] <= 3:
            for path in ip_data['paths'][:5]:
                print(f"      - {path}")

        print(f"   ⚠️  Razones de sospecha:")
        for reason in ip_data['suspicious_reasons']:
            print(f"      • {reason}")

        print(f"\n   💡 Recomendaciones:")
        if ip_data['requests_per_window'] >= 20:
            print(f"      • Implementar rate limiting estricto (máx 10 solicitudes/minuto)")
        if ip_data['std_dev_interval'] < 2:
            print(f"      • Posible bot - considerar bloqueo temporal")
        if ip_data['unique_paths'] == 1:
            print(f"      • Monitorear endpoint específico: {ip_data['paths'][0]}")
        print("-"*80)

    print("\n" + "="*80)
    print("📋 RESUMEN DE RECOMENDACIONES")
    print("="*80)
    print("\n1. Implementar Rate Limiting:")
    print("   - Límite general: 60 solicitudes/minuto por IP")
    print("   - Límite estricto para endpoints sensibles: 10 solicitudes/minuto")
    print("   - Usar slowapi o similar para implementación")

    print("\n2. Monitoreo Continuo:")
    print("   - Configurar alertas para IPs con >20 solicitudes/minuto")
    print("   - Registrar intentos sospechosos en base de datos")

    print("\n3. Protección Adicional:")
    print("   - Considerar CAPTCHA para patrones repetitivos")
    print("   - Implementar bloqueo temporal automático")
    print("   - Revisar logs de autenticación para estas IPs")

    print("\n" + "="*80)


def main():
    parser = argparse.ArgumentParser(
        description="Analizar logs y detectar patrones anómalos de seguridad",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python scripts/analizar_logs_seguridad.py logs/app.log
  python scripts/analizar_logs_seguridad.py logs/app.log --window 60 --threshold 10
  python scripts/analizar_logs_seguridad.py logs/app.log --window 30 --threshold 5
        """
    )
    parser.add_argument(
        "log_file",
        type=Path,
        help="Ruta al archivo de log a analizar"
    )
    parser.add_argument(
        "--window",
        type=int,
        default=60,
        help="Ventana de tiempo en segundos para calcular frecuencia (default: 60)"
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=10,
        help="Umbral mínimo de solicitudes por ventana para considerar sospechoso (default: 10)"
    )

    args = parser.parse_args()

    if not args.log_file.exists():
        print(f"❌ Error: Archivo no encontrado: {args.log_file}", file=sys.stderr)
        sys.exit(1)

    print(f"🔍 Analizando logs de seguridad: {args.log_file}")
    print(f"⏱️  Ventana: {args.window}s")
    print(f"📊 Umbral: {args.threshold} solicitudes")
    print(f"📖 Leyendo archivo...")

    logs = []
    total_lines = 0
    parsed_lines = 0

    try:
        with open(args.log_file, 'r', encoding='utf-8') as f:
            for line in f:
                total_lines += 1
                parsed = parse_log_line(line)
                if parsed:
                    parsed_lines += 1
                    logs.append(parsed)
    except Exception as e:
        print(f"❌ Error leyendo archivo: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"✅ Líneas procesadas: {total_lines:,}")
    print(f"✅ Líneas parseadas: {parsed_lines:,}")
    print(f"🔍 Analizando patrones...")

    analysis = analyze_suspicious_patterns(logs, window_seconds=args.window, threshold=args.threshold)
    print_report(analysis)


if __name__ == "__main__":
    main()

