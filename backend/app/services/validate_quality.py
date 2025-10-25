# !/usr/bin/env python3"""Script de Validación de Calidad para ServicesAplica normas de linting, formateo y
# import configure_service_loggingfrom app.services.quality_standards import apply_quality_standards# Agregar el directorio
# del proyecto al pathsys.path.append(str(Path(__file__).parent.parent.parent))def _configurar_logging_y_directorio():
# """Configurar logging y verificar directorio""" print("APLICANDO NORMAS DE CALIDAD A BACKEND/APP/SERVICES") print("=" * 60)
# services_dir.exists(): print(f"Error: Directorio {services_dir} no existe") return None print(f"Analizando directorio:
# {services_dir}") print() return services_dirdef _ejecutar_analisis_calidad(services_dir: Path): """Ejecutar análisis de
# * 40) for service in report["services"]: service_name = Path(service["file_path"]).name score = service["score"] # Color
# del score if score >= 90: score_color = "VERDE" elif score >= 80: score_color = "AMARILLO" elif score >= 70: score_color =
# específicas validations = service["validations"] for validation, passed in validations.items(): status = "OK" if passed
# not in service["metrics"]: metrics = service["metrics"] print(f" Funciones: {metrics.get('total_functions', 0)}") print(f"
# Clases: {metrics.get('total_classes', 0)}") print(f" Lineas: {metrics.get('total_lines', 0)}") print(f" Complejidad:
# report["critical_issues"]: print(f"ERROR {issue['file']}: {issue['score']:.2f}%") for problem in issue["issues"]: print(f"
# report["recommendations"]: print("RECOMENDACIONES") print("-" * 40) for i, recommendation in
# enumerate(report["recommendations"], 1): print(f"{i}. {recommendation}") print()def _guardar_reporte(report: dict) -> Path:
# """Guardar reporte en archivo""" report_file = ( Path(__file__).parent /
# json.dump(report, f, indent=2, ensure_ascii=False) print(f"Reporte guardado en: {report_file}") return report_filedef
# _determinar_codigo_salida(overall_score: float) -> int: """Determinar código de salida según score""" if overall_score >=
# 80: print("Calidad aceptable") return 0 elif overall_score >= 70: print("Calidad mejorable") return 1 else: print("Calidad
# insuficiente") return 2def main(): """ Función principal del script de validación (VERSIÓN REFACTORIZADA) """ # Configurar
# logging y directorio services_dir = _configurar_logging_y_directorio() if services_dir is None: return 1 # Ejecutar
# reporte _guardar_reporte(report) # Determinar código de salida return _determinar_codigo_salida(report["overall_score"])if
# __name__ == "__main__": exit_code = main() sys.exit(exit_code)
