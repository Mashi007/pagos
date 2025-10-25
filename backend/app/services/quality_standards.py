# backend/app/services/quality_standards.py
"""
Normas de Calidad para Services
Implementa estándares de desarrollo y monitoreo
"""

import ast
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class QualityStandards:
    """
    Clase para validar y aplicar normas de calidad en servicios
    """

    # Configuración de normas
    MAX_FUNCTION_LINES = 50
    MAX_FUNCTION_PARAMS = 5
    MAX_CYCLOMATIC_COMPLEXITY = 10
    MAX_LINE_LENGTH = 120
    INDENTATION_SIZE = 4

    # Palabras prohibidas en producción
    FORBIDDEN_WORDS = [
        "console.log",
        "print(",
        "debugger",
        "TODO",
        "FIXME",
        "HACK",
        "XXX",
        "TEMP",
        "TEMPORARY",
        "TEST",
        "DEBUG",
    ]

    # Patrones de código problemático
    PROBLEMATIC_PATTERNS = [
        r"==\s*[^=]",  # == en lugar de ===
        r"var\s+\w+",  # uso de var
        r"eval\(",  # uso de eval
        r"setTimeout\(",  # setTimeout sin manejo de errores
    ]

    @staticmethod
    def validate_file_structure(file_path: str) -> Dict[str, Any]:
        """
        Validar estructura y organización del archivo
        """
        results = {"file_path": file_path, "validations": {}, "issues": [], "score": 0}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Validaciones de estructura
            results["validations"]["has_docstring"] = QualityStandards._has_module_docstring(
                content
            )
            results["validations"]["proper_imports"] = QualityStandards._validate_imports(content)
            results["validations"]["class_structure"] = QualityStandards._validate_class_structure(
                content
            )
            results["validations"]["function_length"] = QualityStandards._validate_function_length(
                content
            )
            results["validations"]["line_length"] = QualityStandards._validate_line_length(content)
            results["validations"]["indentation"] = QualityStandards._validate_indentation(content)
            results["validations"]["forbidden_words"] = QualityStandards._check_forbidden_words(
                content
            )
            results["validations"]["error_handling"] = QualityStandards._validate_error_handling(
                content
            )
            results["validations"]["logging"] = QualityStandards._validate_logging(content)

            # Calcular score
            total_validations = len(results["validations"])
            passed_validations = sum(1 for v in results["validations"].values() if v)
            results["score"] = round((passed_validations / total_validations) * 100, 2)

        except Exception as e:
            results["issues"].append(f"Error validando archivo: {str(e)}")

        return results

    @staticmethod
    def _has_module_docstring(content: str) -> bool:
        """Verificar si el módulo tiene docstring"""
        lines = content.split("\n")
        if not lines:
            return False

        # Buscar docstring al inicio del archivo
        for line in lines[:10]:  # Buscar en las primeras 10 líneas
            if '"""' in line or "'''" in line:
                return True
        return False

    @staticmethod
    def _validate_imports(content: str) -> bool:
        """Validar organización de imports"""
        lines = content.split("\n")
        import_lines = [line for line in lines if line.strip().startswith(("import ", "from "))]

        if not import_lines:
            return True

        # Verificar que imports externos vengan antes que internos
        external_imports = []
        internal_imports = []

        for line in import_lines:
            if "app." in line or line.strip().startswith("from ."):
                internal_imports.append(line)
            else:
                external_imports.append(line)

        # Verificar orden
        if external_imports and internal_imports:
            last_external_idx = lines.index(external_imports[-1])
            first_internal_idx = lines.index(internal_imports[0])
            return last_external_idx < first_internal_idx

        return True

    @staticmethod
    def _validate_class_structure(content: str) -> bool:
        """Validar estructura de clases"""
        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Verificar que la clase tenga docstring
                    if not (
                        node.body
                        and isinstance(node.body[0], ast.Expr)
                        and isinstance(node.body[0].value, ast.Constant)
                    ):
                        return False

                    # Verificar métodos
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            # Verificar que métodos públicos tengan docstring
                            if not item.name.startswith("_") and not (
                                item.body
                                and isinstance(item.body[0], ast.Expr)
                                and isinstance(item.body[0].value, ast.Constant)
                            ):
                                return False

            return True
        except Exception:
            return False

    @staticmethod
    def _validate_function_length(content: str) -> bool:
        """Validar longitud de funciones"""
        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    lines = len(node.body)
                    if lines > QualityStandards.MAX_FUNCTION_LINES:
                        return False

            return True
        except Exception:
            return False

    @staticmethod
    def _validate_line_length(content: str) -> bool:
        """Validar longitud de líneas"""
        lines = content.split("\n")
        for line in lines:
            if len(line) > QualityStandards.MAX_LINE_LENGTH:
                return False
        return True

    @staticmethod
    def _validate_indentation(content: str) -> bool:
        """Validar consistencia de indentación"""
        lines = content.split("\n")

        for line in lines:
            if line.strip():  # Línea no vacía
                # Contar espacios al inicio
                spaces = len(line) - len(line.lstrip())
                if spaces > 0 and spaces % QualityStandards.INDENTATION_SIZE != 0:
                    return False

        return True

    @staticmethod
    def _check_forbidden_words(content: str) -> bool:
        """Verificar palabras prohibidas"""
        content_upper = content.upper()
        for word in QualityStandards.FORBIDDEN_WORDS:
            if word.upper() in content_upper:
                return False
        return True

    @staticmethod
    def _validate_error_handling(content: str) -> bool:
        """Validar manejo de errores"""
        # Buscar funciones que podrían lanzar excepciones
        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Verificar si la función tiene try/except o manejo de errores
                    has_error_handling = False

                    for item in node.body:
                        if isinstance(item, (ast.Try, ast.Raise)):
                            has_error_handling = True
                            break

                    # Si la función hace llamadas externas, debería tener manejo de errores
                    has_external_calls = False
                    for item in ast.walk(node):
                        if isinstance(item, ast.Call):
                            if isinstance(item.func, ast.Attribute):
                                has_external_calls = True
                                break

                    if has_external_calls and not has_error_handling:
                        return False

            return True
        except Exception:
            return False

    @staticmethod
    def _validate_logging(content: str) -> bool:
        """Validar uso de logging estructurado"""
        # Verificar que se use logging en lugar de print
        if "print(" in content and "logging" not in content:
            return False

        # Verificar que se importe logging
        if "logging" in content and "import logging" not in content:
            return False

        return True

    @staticmethod
    def generate_quality_report(services_dir: str) -> Dict[str, Any]:
        """
        Generar reporte de calidad para todos los servicios
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "services_analyzed": 0,
            "overall_score": 0,
            "services": [],
            "recommendations": [],
            "critical_issues": [],
        }

        services_path = Path(services_dir)
        if not services_path.exists():
            return report

        service_files = list(services_path.glob("*.py"))
        report["services_analyzed"] = len(service_files)

        total_score = 0
        for service_file in service_files:
            if service_file.name.startswith("__"):
                continue

            file_report = QualityStandards.validate_file_structure(str(service_file))
            report["services"].append(file_report)
            total_score += file_report["score"]

            # Identificar problemas críticos
            if file_report["score"] < 70:
                report["critical_issues"].append(
                    {
                        "file": service_file.name,
                        "score": file_report["score"],
                        "issues": file_report["issues"],
                    }
                )

        if report["services_analyzed"] > 0:
            report["overall_score"] = round(total_score / report["services_analyzed"], 2)

        # Generar recomendaciones
        report["recommendations"] = QualityStandards._generate_recommendations(report)

        return report

    @staticmethod
    def _generate_recommendations(report: Dict[str, Any]) -> List[str]:
        """Generar recomendaciones basadas en el reporte"""
        recommendations = []

        if report["overall_score"] < 80:
            recommendations.append("Implementar logging estructurado en todos los servicios")
            recommendations.append("Agregar docstrings a todas las clases y métodos públicos")
            recommendations.append("Implementar manejo de errores consistente")

        if report["overall_score"] < 70:
            recommendations.append("Revisar longitud de funciones (máximo 50 líneas)")
            recommendations.append("Eliminar palabras prohibidas de producción")
            recommendations.append("Implementar validación de entrada en todos los métodos")

        if report["overall_score"] < 60:
            recommendations.append("Refactorizar código con alta complejidad ciclomática")
            recommendations.append("Implementar tests unitarios para todos los servicios")
            recommendations.append("Revisar arquitectura y separación de responsabilidades")

        return recommendations


class ServiceMetrics:
    """
    Clase para métricas de servicios
    """

    @staticmethod
    def calculate_complexity_metrics(content: str) -> Dict[str, Any]:
        """
        Calcular métricas de complejidad del código
        """
        try:
            tree = ast.parse(content)

            metrics = {
                "total_functions": 0,
                "total_classes": 0,
                "total_lines": len(content.split("\n")),
                "cyclomatic_complexity": 0,
                "average_function_length": 0,
                "max_function_length": 0,
            }

            function_lengths = []

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    metrics["total_functions"] += 1
                    function_length = len(node.body)
                    function_lengths.append(function_length)
                    metrics["max_function_length"] = max(
                        metrics["max_function_length"], function_length
                    )

                    # Calcular complejidad ciclomática básica
                    complexity = 1  # Base complexity
                    for item in ast.walk(node):
                        if isinstance(item, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                            complexity += 1
                    metrics["cyclomatic_complexity"] += complexity

                elif isinstance(node, ast.ClassDef):
                    metrics["total_classes"] += 1

            if function_lengths:
                metrics["average_function_length"] = sum(function_lengths) / len(function_lengths)

            return metrics

        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def generate_performance_recommendations(metrics: Dict[str, Any]) -> List[str]:
        """
        Generar recomendaciones de rendimiento basadas en métricas
        """
        recommendations = []

        if metrics.get("average_function_length", 0) > 30:
            recommendations.append("Considerar dividir funciones largas en funciones más pequeñas")

        if metrics.get("cyclomatic_complexity", 0) > 20:
            recommendations.append("Reducir complejidad ciclomática usando patrones de diseño")

        if metrics.get("max_function_length", 0) > 50:
            recommendations.append("Refactorizar función más larga para mejorar legibilidad")

        if metrics.get("total_functions", 0) > 20:
            recommendations.append("Considerar dividir el módulo en múltiples archivos")

        return recommendations


# Función de utilidad para aplicar normas automáticamente


def apply_quality_standards(services_dir: str) -> Dict[str, Any]:
    """
    Aplicar normas de calidad y generar reporte
    """
    report = QualityStandards.generate_quality_report(services_dir)

    # Agregar métricas detalladas
    for service in report["services"]:
        try:
            with open(service["file_path"], "r", encoding="utf-8") as f:
                content = f.read()
            service["metrics"] = ServiceMetrics.calculate_complexity_metrics(content)
            service["performance_recommendations"] = (
                ServiceMetrics.generate_performance_recommendations(service["metrics"])
            )
        except Exception as e:
            service["metrics"] = {"error": str(e)}

    return report
