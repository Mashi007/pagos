#!/usr/bin/env python3
"""
Script de Validación de Calidad para Services
Aplica normas de linting, formateo y trazabilidad
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Agregar el directorio del proyecto al path
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.services.logging_config import configure_service_logging
from app.services.quality_standards import apply_quality_standards


def main():
    """
    Función principal del script de validación
    """
    print("APLICANDO NORMAS DE CALIDAD A BACKEND/APP/SERVICES")
    print("=" * 60)

    # Configurar logging
    configure_service_logging()

    # Directorio de servicios
    services_dir = Path(__file__).parent

    if not services_dir.exists():
        print(f"Error: Directorio {services_dir} no existe")
        return 1

    print(f"Analizando directorio: {services_dir}")
    print()

    # Aplicar normas de calidad
    print("Ejecutando analisis de calidad...")
    report = apply_quality_standards(str(services_dir))

    # Mostrar resultados
    print("RESULTADOS DEL ANALISIS")
    print("-" * 40)
    print(f"Servicios analizados: {report['services_analyzed']}")
    print(f"Score general: {report['overall_score']:.2f}%")
    print(f"Timestamp: {report['timestamp']}")
    print()

    # Mostrar detalles por servicio
    print("DETALLES POR SERVICIO")
    print("-" * 40)

    for service in report["services"]:
        service_name = Path(service["file_path"]).name
        score = service["score"]

        # Color del score
        if score >= 90:
            score_color = "VERDE"
        elif score >= 80:
            score_color = "AMARILLO"
        elif score >= 70:
            score_color = "NARANJA"
        else:
            score_color = "ROJO"

        print(f"{score_color} {service_name}: {score:.2f}%")

        # Mostrar validaciones específicas
        validations = service["validations"]
        for validation, passed in validations.items():
            status = "OK" if passed else "ERROR"
            print(f"   {status} {validation}")

        # Mostrar métricas si están disponibles
        if "metrics" in service and "error" not in service["metrics"]:
            metrics = service["metrics"]
            print(f"   Funciones: {metrics.get('total_functions', 0)}")
            print(f"   Clases: {metrics.get('total_classes', 0)}")
            print(f"   Lineas: {metrics.get('total_lines', 0)}")
            print(f"   Complejidad: {metrics.get('cyclomatic_complexity', 0)}")

        print()

    # Mostrar problemas críticos
    if report["critical_issues"]:
        print("PROBLEMAS CRITICOS")
        print("-" * 40)
        for issue in report["critical_issues"]:
            print(f"ERROR {issue['file']}: {issue['score']:.2f}%")
            for problem in issue["issues"]:
                print(f"   • {problem}")
        print()

    # Mostrar recomendaciones
    if report["recommendations"]:
        print("RECOMENDACIONES")
        print("-" * 40)
        for i, recommendation in enumerate(report["recommendations"], 1):
            print(f"{i}. {recommendation}")
        print()

    # Guardar reporte
    report_file = (
        Path(__file__).parent
        / f"quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"Reporte guardado en: {report_file}")

    # Determinar código de salida
    if report["overall_score"] >= 80:
        print("Calidad aceptable")
        return 0
    elif report["overall_score"] >= 70:
        print("Calidad mejorable")
        return 1
    else:
        print("Calidad insuficiente")
        return 2


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
